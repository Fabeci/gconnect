"""E3.2 HTTP regression tests for isolated, revocable privileged web sessions."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import (
    EstablishmentWebSession, InstitutionAdmin, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import (
    encrypt_totp, generate_recovery_codes, generate_totp_secret,
)
from apps.api.v1.users.privileged_views import PrivilegedMFAVerifyView
from apps.api.v1.users.throttles import OtpThrottle
from apps.api.v1.users.throttles import LoginThrottle
from apps.api.v1.users.views import ChangePasswordView, MeView
from apps.api.v1.users.web_authentication import (
    EstablishmentWebTokenAuthentication, WEB_SESSION_COOKIE_NAME,
)
from apps.api.v1.users.web_views import (
    EstablishmentWebLoginView, EstablishmentWebLogoutView,
    EstablishmentWebRevokeSessionView, EstablishmentWebSessionsView,
    EstablishmentWebResumeView,
)


class EstablishmentWebSessionHttpTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.institution = Institution.objects.create(name="E3 Web School", acronym="E3")
        self.user = User.objects.create_user(
            username="e3_admin", email="e3-admin@example.test",
            password="E3-Secure-Test-Password!", role="etablissement", is_active=True,
        )
        InstitutionAdmin.objects.create(user=self.user, institution=self.institution)
        PrivilegedMFADevice.objects.create(
            user=self.user, encrypted_secret=encrypt_totp(generate_totp_secret()),
            confirmed_at=timezone.now(),
        )
        self.recovery_codes = generate_recovery_codes(self.user)
        self.student = User.objects.create_user(
            username="e3_student", email="e3-student@example.test",
            password="E3-Secure-Test-Password!", role="student", is_active=True,
        )

    def login(self, *, user=None, password="E3-Secure-Test-Password!"):
        user = user or self.user
        request = self.factory.post(
            "/api/v1/users/web-login/",
            {"email": user.email, "password": password}, format="json",
            HTTP_USER_AGENT="E3 Browser Test",
        )
        with patch.object(LoginThrottle, "allow_request", return_value=True):
            first = EstablishmentWebLoginView.as_view()(request)
        if first.status_code != 200 or user.pk != self.user.pk:
            return first
        verify_request = self.factory.post(
            "/api/v1/users/web-mfa/verify/",
            {"challenge": first.data["data"]["challenge"], "code": self.recovery_codes.pop(0)},
            format="json",
        )
        with patch.object(OtpThrottle, "allow_request", return_value=True):
            return PrivilegedMFAVerifyView.as_view()(verify_request)

    def request_with_token(self, method, path, token, view_class, *, data=None, **url_params):
        request = getattr(self.factory, method)(
            path, data=data or {}, format="json",
            HTTP_AUTHORIZATION=f"WebToken {token}",
        )
        return view_class.as_view()(request, **url_params)

    def test_school_login_creates_only_hashed_per_device_token(self):
        first = self.login()
        self.assertEqual(first.status_code, 200, getattr(first, "data", None))
        raw = first.data["data"]["token"]
        self.assertEqual(first.data["data"]["token_type"], "WebToken")
        second = self.login()
        self.assertEqual(second.status_code, 200, getattr(second, "data", None))
        self.assertNotEqual(raw, second.data["data"]["token"])
        self.assertEqual(EstablishmentWebSession.objects.filter(user=self.user).count(), 2)
        self.assertFalse(EstablishmentWebSession.objects.filter(token_hash=raw).exists())
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        me = self.request_with_token(
            "get", "/api/v1/users/me/", raw, MeView,
        )
        self.assertEqual(me.status_code, 200, getattr(me, "data", None))
        self.assertEqual(me.data["data"]["institution_id"], self.institution.pk)

    def test_legacy_mobile_token_works_independently(self):
        student_token = Token.objects.create(user=self.student)
        request = self.factory.get(
            "/api/v1/users/me/", HTTP_AUTHORIZATION=f"Token {student_token.key}",
        )
        response = MeView.as_view()(request)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.assertEqual(response.data["data"]["role"], "student")
        self.assertFalse(EstablishmentWebSession.objects.filter(user=self.student).exists())
        # A privileged user's old Flutter token no longer bypasses E4 MFA.
        admin_token = Token.objects.create(user=self.user)
        denied = MeView.as_view()(self.factory.get(
            "/api/v1/users/me/", HTTP_AUTHORIZATION=f"Token {admin_token.key}",
        ))
        self.assertEqual(denied.status_code, 401)

    def test_web_login_caps_concurrent_sessions_per_user(self):
        credentials = [self.login().data["data"]["token"] for _ in range(6)]
        active = EstablishmentWebSession.objects.filter(
            user=self.user, revoked_at__isnull=True,
        ).count()
        self.assertEqual(active, 5)
        first = self.request_with_token("get", "/api/v1/users/me/", credentials[0], MeView)
        self.assertEqual(first.status_code, 401)
        latest = self.request_with_token("get", "/api/v1/users/me/", credentials[-1], MeView)
        self.assertEqual(latest.status_code, 200)

    def test_students_have_no_privileged_web_login(self):
        response = self.login(user=self.student)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(EstablishmentWebSession.objects.filter(user=self.student).exists())

    def test_logout_revokes_only_its_device(self):
        first = self.login().data["data"]["token"]
        second = self.login().data["data"]["token"]
        logout = self.request_with_token(
            "post", "/api/v1/users/web-logout/", first, EstablishmentWebLogoutView,
        )
        self.assertEqual(logout.status_code, 200)
        rejected = self.request_with_token("get", "/api/v1/users/me/", first, MeView)
        self.assertEqual(rejected.status_code, 401)
        allowed = self.request_with_token("get", "/api/v1/users/me/", second, MeView)
        self.assertEqual(allowed.status_code, 200)

    def test_session_list_and_ownership_bound_revoke(self):
        current = self.login().data["data"]["token"]
        other = self.login().data["data"]["token"]
        listing = self.request_with_token(
            "get", "/api/v1/users/web-sessions/", current, EstablishmentWebSessionsView,
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["data"]), 2)
        self.assertEqual(sum(bool(s["current"]) for s in listing.data["data"]), 1)
        session, _ = EstablishmentWebSession.issue(self.student, self.factory.get("/"))
        # The student cannot log in; this is an independent fixture to test
        # that another user's device ID cannot be used for targeted revocation.
        foreign = self.request_with_token(
            "post", f"/api/v1/users/web-sessions/{session.pk}/revoke/",
            current, EstablishmentWebRevokeSessionView, session_id=session.pk,
        )
        self.assertEqual(foreign.status_code, 404)
        self.assertIsNone(EstablishmentWebSession.objects.get(pk=session.pk).revoked_at)
        other_session = EstablishmentWebSession.objects.get(
            token_hash=__import__("hashlib").sha256(other.encode("ascii")).hexdigest(),
        )
        allowed = self.request_with_token(
            "post", f"/api/v1/users/web-sessions/{other_session.pk}/revoke/",
            current, EstablishmentWebRevokeSessionView, session_id=other_session.pk,
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(self.request_with_token("get", "/api/v1/users/me/", other, MeView).status_code, 401)
        self.assertEqual(self.request_with_token("get", "/api/v1/users/me/", current, MeView).status_code, 200)

    def test_expiration_and_inactivity_revoke_sessions(self):
        raw = self.login().data["data"]["token"]
        session = EstablishmentWebSession.objects.get(user=self.user)
        session.last_seen_at = timezone.now() - timedelta(minutes=60)
        session.save(update_fields=["last_seen_at"])
        auth = EstablishmentWebTokenAuthentication()
        req = self.factory.get("/", HTTP_AUTHORIZATION=f"WebToken {raw}")
        with self.assertRaises(AuthenticationFailed):
            auth.authenticate(req)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)

        raw = self.login().data["data"]["token"]
        session = EstablishmentWebSession.objects.filter(user=self.user, revoked_at__isnull=True).get()
        session.expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=["expires_at"])
        with self.assertRaises(AuthenticationFailed):
            auth.authenticate(self.factory.get("/", HTTP_AUTHORIZATION=f"WebToken {raw}"))

    def test_inactive_institution_and_banned_account_rejected(self):
        raw = self.login().data["data"]["token"]
        self.institution.is_active = False
        self.institution.save(update_fields=["is_active"])
        blocked = self.request_with_token("get", "/api/v1/users/me/", raw, MeView)
        self.assertEqual(blocked.status_code, 401)
        self.institution.is_active = True
        self.institution.save(update_fields=["is_active"])
        raw = self.login().data["data"]["token"]
        self.user.is_banned = True
        self.user.save(update_fields=["is_banned"])
        blocked = self.request_with_token("get", "/api/v1/users/me/", raw, MeView)
        self.assertEqual(blocked.status_code, 401)

    def test_password_change_revokes_web_sessions_without_creating_mobile_token(self):
        raw = self.login().data["data"]["token"]
        response = self.request_with_token(
            "post", "/api/v1/users/me/change-password/", raw, ChangePasswordView,
            data={
                "current_password": "E3-Secure-Test-Password!",
                "new_password": "Another-Secure-Test-Password!",
            },
        )
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.assertTrue(response.data["data"]["requires_relogin"])
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertEqual(
            EstablishmentWebSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 0,
        )

    @override_settings(CORS_ALLOWED_ORIGINS=["http://127.0.0.1:8094"])
    def test_mfa_verified_cookie_restores_one_live_device_without_another_mfa(self):
        authenticated = self.login()
        self.assertEqual(authenticated.status_code, 200)
        raw = authenticated.data["data"]["token"]
        cookie = authenticated.cookies[WEB_SESSION_COOKIE_NAME]
        self.assertEqual(cookie.value, raw)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["path"], "/api/v1/users/")
        self.assertGreater(int(cookie["max-age"]), 0)

        request = self.factory.post(
            "/api/v1/users/web-resume/", {}, format="json",
            HTTP_ORIGIN="http://127.0.0.1:8094",
            HTTP_COOKIE=f"{WEB_SESSION_COOKIE_NAME}={raw}",
        )
        restored = EstablishmentWebResumeView.as_view()(request)
        self.assertEqual(restored.status_code, 200, getattr(restored, "data", None))
        self.assertEqual(restored.data["data"]["token_type"], "WebToken")
        self.assertEqual(restored.data["data"]["token"], raw)
        self.assertEqual(restored.data["data"]["role"], "etablissement")
        self.assertEqual(EstablishmentWebSession.objects.filter(user=self.user).count(), 1)

        me = self.request_with_token("get", "/api/v1/users/me/", raw, MeView)
        self.assertEqual(me.status_code, 200)

    @override_settings(CORS_ALLOWED_ORIGINS=["http://127.0.0.1:8094"])
    def test_resume_rejects_other_origins_and_expired_or_revoked_sessions(self):
        authenticated = self.login()
        raw = authenticated.data["data"]["token"]

        def resume(origin):
            return EstablishmentWebResumeView.as_view()(self.factory.post(
                "/api/v1/users/web-resume/", {}, format="json",
                HTTP_ORIGIN=origin,
                HTTP_COOKIE=f"{WEB_SESSION_COOKIE_NAME}={raw}",
            ))

        self.assertEqual(resume("https://evil.example").status_code, 403)
        self.assertEqual(resume("http://127.0.0.1:8094").status_code, 200)

        logout = self.request_with_token(
            "post", "/api/v1/users/web-logout/", raw, EstablishmentWebLogoutView,
        )
        self.assertEqual(logout.status_code, 200)
        self.assertIn(WEB_SESSION_COOKIE_NAME, logout.cookies)
        self.assertEqual(logout.cookies[WEB_SESSION_COOKIE_NAME].value, "")
        revoked = resume("http://127.0.0.1:8094")
        self.assertEqual(revoked.status_code, 401)
        self.assertIn(WEB_SESSION_COOKIE_NAME, revoked.cookies)

        latest = self.login().data["data"]["token"]
        session = EstablishmentWebSession.objects.get(
            token_hash=__import__("hashlib").sha256(latest.encode("ascii")).hexdigest(),
        )
        session.last_seen_at = timezone.now() - timedelta(minutes=60)
        session.save(update_fields=["last_seen_at"])
        expired = EstablishmentWebResumeView.as_view()(self.factory.post(
            "/api/v1/users/web-resume/", {}, format="json",
            HTTP_ORIGIN="http://127.0.0.1:8094",
            HTTP_COOKIE=f"{WEB_SESSION_COOKIE_NAME}={latest}",
        ))
        self.assertEqual(expired.status_code, 401)
