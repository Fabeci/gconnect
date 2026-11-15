"""E4 regression tests for enterprise admin invitation, activation and mandatory TOTP."""
import hashlib
import re
import time
from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.establishments.permissions import IsInstitutionManager
from apps.api.v1.publicapi.models import ApiKey
from apps.api.v1.users.models import (
    EstablishmentInvitation, EstablishmentWebSession, InstitutionAdmin,
    PrivilegedMFADevice, PrivilegedRecoveryCode, User,
)
from apps.api.v1.users.privileged_security import (
    _totp, encrypt_totp, generate_totp_secret, token_digest,
)
from apps.api.v1.users.privileged_views import (
    EstablishmentInvitationAcceptView, EstablishmentInvitationPreviewView,
    EstablishmentInvitationRevokeView, EstablishmentInvitationsView,
    PrivilegedMFASetupView, PrivilegedMFAVerifyView,
)
from apps.api.v1.users.throttles import LoginThrottle, OtpThrottle, RegistrationThrottle
from apps.api.v1.users.views import LoginView, MeView
from apps.api.v1.users.web_views import EstablishmentWebLoginView


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    GCONNECT_WEB_APP_URL="https://gconnect.example.test",
)
class PrivilegedAuthE4Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.institution = Institution.objects.create(name="E4 Institut", acronym="E4")
        self.superadmin = User.objects.create_user(
            username="e4_root", email="root-e4@example.test",
            password="E4-Strong-Password!", role="superAdmin", is_active=True,
        )
        self.student = User.objects.create_user(
            username="e4_student", email="student-e4@example.test",
            password="E4-Strong-Password!", role="student", is_active=True,
        )
        secret = generate_totp_secret()
        PrivilegedMFADevice.objects.create(
            user=self.superadmin, encrypted_secret=encrypt_totp(secret),
            confirmed_at=timezone.now(),
        )
        _, self.super_token = EstablishmentWebSession.issue(
            self.superadmin, self.factory.post("/"),
        )

    def call(self, view, path, *, method="post", token=None, auth_scheme="WebToken", data=None, **kwargs):
        args = {"format": "json"}
        if token:
            args["HTTP_AUTHORIZATION"] = f"{auth_scheme} {token}"
        request = getattr(self.factory, method)(path, data=data or {}, **args)
        with patch.object(RegistrationThrottle, "allow_request", return_value=True), \
             patch.object(OtpThrottle, "allow_request", return_value=True), \
             patch.object(LoginThrottle, "allow_request", return_value=True):
            return view.as_view()(request, **kwargs)

    def invite(self, email="invite-e4@example.test"):
        response = self.call(
            EstablishmentInvitationsView, "/api/v1/users/admin/invitations/",
            token=self.super_token, data={"email": email, "institution_id": self.institution.pk},
        )
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        raw = re.search(r"#invitation=([^\s]+)", mail.outbox[-1].body).group(1)
        return response, raw

    def accept(self, raw, password="E4-New-Account-Password!"):
        return self.call(
            EstablishmentInvitationAcceptView, "/api/v1/users/invitations/accept/",
            data={"invitation": raw, "password": password, "first_name": "Admin", "last_name": "École"},
        )

    def login(self, email="invite-e4@example.test", password="E4-New-Account-Password!"):
        return self.call(
            EstablishmentWebLoginView, "/api/v1/users/web-login/",
            data={"email": email, "password": password},
        )

    def test_only_superadmin_can_send_and_revoke_invitations(self):
        student_token = Token.objects.create(user=self.student)
        blocked = self.call(
            EstablishmentInvitationsView, "/api/v1/users/admin/invitations/",
            token=student_token.key, auth_scheme="Token", data={"email": "a@example.test", "institution_id": self.institution.pk},
        )
        self.assertEqual(blocked.status_code, 401)
        sent, raw = self.invite()
        self.assertNotIn(raw, str(sent.data))
        saved = EstablishmentInvitation.objects.get(pk=sent.data["data"]["id"])
        self.assertEqual(saved.token_hash, hashlib.sha256(raw.encode("ascii")).hexdigest())
        self.assertNotIn(raw, str(saved.__dict__))
        self.assertIn("etablissement-activation.html#invitation=", mail.outbox[-1].body)
        invalid = self.call(
            EstablishmentInvitationPreviewView, "/api/v1/users/invitations/preview/",
            data={"invitation": "bogus"},
        )
        self.assertEqual(invalid.status_code, 400)
        revoked = self.call(
            EstablishmentInvitationRevokeView,
            f"/api/v1/users/admin/invitations/{saved.pk}/revoke/",
            token=self.super_token, invitation_id=saved.pk,
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(self.accept(raw).status_code, 400)

    def test_invitation_expiration_and_single_use(self):
        _, raw = self.invite()
        entry = EstablishmentInvitation.objects.get(token_hash=token_digest(raw))
        entry.expires_at = timezone.now() - timedelta(seconds=1)
        entry.save(update_fields=["expires_at"])
        self.assertEqual(self.accept(raw).status_code, 400)
        _, raw = self.invite()
        preview = self.call(
            EstablishmentInvitationPreviewView, "/api/v1/users/invitations/preview/",
            data={"invitation": raw},
        )
        self.assertEqual(preview.status_code, 200)
        result = self.accept(raw)
        self.assertEqual(result.status_code, 200, getattr(result, "data", None))
        self.assertEqual(self.accept(raw).status_code, 400)
        user = User.objects.get(email="invite-e4@example.test")
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, "etablissement")
        self.assertTrue(user.check_password("E4-New-Account-Password!"))
        self.assertEqual(InstitutionAdmin.objects.get(user=user).institution, self.institution)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_smtp_failure_rolls_back_invitation(self):
        with patch("apps.api.v1.users.privileged_views.send_mail", return_value=0):
            result = self.call(
                EstablishmentInvitationsView, "/api/v1/users/admin/invitations/",
                token=self.super_token, data={"email": "fail-e4@example.test", "institution_id": self.institution.pk},
            )
        self.assertEqual(result.status_code, 503)
        self.assertFalse(EstablishmentInvitation.objects.filter(email="fail-e4@example.test").exists())

    def test_invitation_accept_requires_strong_password(self):
        _, raw = self.invite()
        weak = self.accept(raw, password="123")
        self.assertEqual(weak.status_code, 400)
        self.assertFalse(User.objects.filter(email="invite-e4@example.test").exists())
        self.assertEqual(self.accept(raw).status_code, 200)

    def test_enrollment_requires_password_then_totp_before_dashboard(self):
        _, raw = self.invite()
        self.assertEqual(self.accept(raw).status_code, 200)
        first = self.login()
        self.assertEqual(first.status_code, 200, getattr(first, "data", None))
        self.assertTrue(first.data["data"]["mfa_required"])
        self.assertEqual(first.data["data"]["mfa_action"], "enroll")
        self.assertNotIn("token", first.data["data"])
        challenge = first.data["data"]["challenge"]
        # A pre-auth challenge is not an access credential.
        premature = self.call(
            MeView, "/api/v1/users/me/", method="get", token=challenge,
        )
        self.assertEqual(premature.status_code, 401)
        setup = self.call(
            PrivilegedMFASetupView, "/api/v1/users/web-mfa/setup/",
            data={"challenge": challenge},
        )
        self.assertEqual(setup.status_code, 200, getattr(setup, "data", None))
        secret = setup.data["data"]["secret"]
        self.assertIn("otpauth://totp/", setup.data["data"]["otpauth_uri"])
        user = User.objects.get(email="invite-e4@example.test")
        device = PrivilegedMFADevice.objects.get(user=user)
        self.assertNotIn(secret, device.encrypted_secret)
        code = _totp(secret, int(time.time()) // 30)
        verified = self.call(
            PrivilegedMFAVerifyView, "/api/v1/users/web-mfa/verify/",
            data={"challenge": challenge, "code": code},
        )
        self.assertEqual(verified.status_code, 200, getattr(verified, "data", None))
        access = verified.data["data"]["token"]
        self.assertEqual(verified.data["data"]["token_type"], "WebToken")
        recovery = verified.data["data"]["recovery_codes"]
        self.assertEqual(len(recovery), 8)
        self.assertFalse(PrivilegedRecoveryCode.objects.filter(code_hash=recovery[0]).exists())
        second_use = self.call(
            PrivilegedMFAVerifyView, "/api/v1/users/web-mfa/verify/",
            data={"challenge": challenge, "code": code},
        )
        self.assertEqual(second_use.status_code, 401)
        me = self.call(MeView, "/api/v1/users/me/", method="get", token=access)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["data"]["institution_id"], self.institution.pk)

        # Code from enrollment is replay-protected; recovery codes are single use.
        new_challenge = self.login().data["data"]["challenge"]
        replay = self.call(
            PrivilegedMFAVerifyView, "/api/v1/users/web-mfa/verify/",
            data={"challenge": new_challenge, "code": code},
        )
        self.assertEqual(replay.status_code, 401)
        recovered = self.call(
            PrivilegedMFAVerifyView, "/api/v1/users/web-mfa/verify/",
            data={"challenge": new_challenge, "code": recovery[0]},
        )
        self.assertEqual(recovered.status_code, 200)
        another_challenge = self.login().data["data"]["challenge"]
        reused = self.call(
            PrivilegedMFAVerifyView, "/api/v1/users/web-mfa/verify/",
            data={"challenge": another_challenge, "code": recovery[0]},
        )
        self.assertEqual(reused.status_code, 401)

    def test_wrong_otp_locks_short_lived_challenge(self):
        _, raw = self.invite()
        self.accept(raw)
        challenge = self.login().data["data"]["challenge"]
        setup = self.call(PrivilegedMFASetupView, "/api/v1/users/web-mfa/setup/", data={"challenge": challenge})
        secret = setup.data["data"]["secret"]
        step_now = int(time.time()) // 30
        valid_steps = {_totp(secret, step_now + drift) for drift in (-1, 0, 1)}
        wrong_code = next(value for value in ("000000", "999999", "111111", "222222") if value not in valid_steps)
        for _ in range(5):
            bad = self.call(
                PrivilegedMFAVerifyView, "/api/v1/users/web-mfa/verify/",
                data={"challenge": challenge, "code": wrong_code},
            )
            self.assertEqual(bad.status_code, 401)
        self.assertEqual(
            self.call(
                PrivilegedMFAVerifyView, "/api/v1/users/web-mfa/verify/",
                data={"challenge": challenge, "code": wrong_code},
            ).status_code,
            401,
        )
        # New password-valid challenges must not reset MFA account lockout.
        self.assertEqual(self.login().status_code, 429)

    def test_django_superuser_flag_does_not_bypass_web_role_gate(self):
        self.student.is_superuser = True
        self.student.save(update_fields=["is_superuser"])
        permission = IsInstitutionManager()
        self.assertFalse(permission.has_object_permission(
            SimpleNamespace(user=self.student), None, self.institution,
        ))

    def test_old_admin_token_and_legacy_login_cannot_bypass_mfa(self):
        admin_token = Token.objects.create(user=self.superadmin)
        response = self.call(MeView, "/api/v1/users/me/", method="get", token=admin_token.key, auth_scheme="Token")
        self.assertEqual(response.status_code, 401)
        legacy = self.call(LoginView, "/api/v1/users/login/",
                           data={"email": self.superadmin.email, "password": "E4-Strong-Password!"})
        self.assertEqual(legacy.status_code, 403)
        self.assertEqual(Token.objects.filter(user=self.superadmin).count(), 1)
        _, api_key = ApiKey.generate(self.superadmin, "old-admin-integration")
        api_denied = MeView.as_view()(self.factory.get(
            "/api/v1/users/me/", HTTP_AUTHORIZATION=f"ApiKey {api_key}",
        ))
        self.assertEqual(api_denied.status_code, 401)
        _, student_api_key = ApiKey.generate(self.student, "student-integration")
        student_allowed = MeView.as_view()(self.factory.get(
            "/api/v1/users/me/", HTTP_AUTHORIZATION=f"ApiKey {student_api_key}",
        ))
        self.assertEqual(student_allowed.status_code, 200)
