"""E54.4: full Django HTTP invitation journey with real MFA and in-memory email.

Nothing calls external SMTP or updates a production database.
"""
import re
import time
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from .models import Enterprise, EnterpriseMember, EstablishmentWebSession, PrivilegedMFADevice, User
from .privileged_security import _totp, encrypt_totp, generate_totp_secret


@override_settings(
    DEBUG=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    GCONNECT_WEB_APP_URL="http://127.0.0.1:5173",
)
class EnterpriseInvitationHTTPJourneyE54Tests(TestCase):
    def setUp(self):
        # This test exercises HTTP/MFA transitions, not rate-limit budgets. E53 uses the same isolation.
        for throttle in ("RegistrationThrottle", "LoginThrottle", "OtpThrottle"):
            p = patch("apps.api.v1.users.throttles." + throttle + ".allow_request", return_value=True)
            p.start()
            self.addCleanup(p.stop)
        self.admin = User.objects.create_user(
            username="e54_http_admin", email="admin-e54-http@example.test",
            password="Complex-Admin-E54!", role="superAdmin", is_active=True,
        )
        PrivilegedMFADevice.objects.create(
            user=self.admin, encrypted_secret=encrypt_totp(generate_totp_secret()),
            confirmed_at=timezone.now(),
        )
        _, raw = EstablishmentWebSession.issue(self.admin, APIRequestFactory().post("/"))
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION="WebToken " + raw)
        self.anonymous = APIClient()

    def invitation_token(self):
        self.assertTrue(mail.outbox, "The Django mail backend must deliver the test invitation.")
        message = mail.outbox[-1].body
        self.assertIn("http://127.0.0.1:5173/entreprise-activation.html#invitation=", message)
        match = re.search(r"#invitation=([A-Za-z0-9_-]{30,128})", message)
        self.assertIsNotNone(match)
        return match.group(1)

    def activate(self, token, email, password="E54-Http-Strong-Password!"):
        preview = self.anonymous.post(reverse("enterprise-invitation-preview"),
                                      {"invitation": token}, format="json")
        self.assertEqual(preview.status_code, 200, getattr(preview, "data", None))
        self.assertEqual(preview.data["data"]["email"], email)
        self.assertNotIn("invitation", preview.data["data"])
        response = self.anonymous.post(reverse("enterprise-invitation-accept"), {
            "invitation": token, "password": password,
            "first_name": "Awa", "last_name": "Traore",
        }, format="json")
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.assertNotIn("token", response.data["data"])
        self.assertEqual(self.anonymous.post(
            reverse("enterprise-invitation-accept"),
            {"invitation": token, "password": password},
            format="json",
        ).status_code, 400, "A valid invitation can be used only once.")
        return password

    def login_with_mfa(self, email, password):
        client = APIClient()
        start = client.post(reverse("web-login"), {"email": email, "password": password}, format="json")
        self.assertEqual(start.status_code, 200, getattr(start, "data", None))
        self.assertNotIn("token", start.data["data"], "No professional token before MFA.")
        challenge = start.data["data"]["challenge"]
        setup = client.post(reverse("web-mfa-setup"), {"challenge": challenge}, format="json")
        self.assertEqual(setup.status_code, 200, getattr(setup, "data", None))
        code = _totp(setup.data["data"]["secret"], int(time.time()) // 30)
        verified = client.post(reverse("web-mfa-verify"), {
            "challenge": challenge, "code": code,
        }, format="json")
        self.assertEqual(verified.status_code, 200, getattr(verified, "data", None))
        self.assertEqual(verified.data["data"]["token_type"], "WebToken")
        client.credentials(HTTP_AUTHORIZATION="WebToken " + verified.data["data"]["token"])
        return client

    def test_superadmin_to_owner_to_recruiter_mfa_and_revocation(self):
        url = reverse("admin-enterprise-invitations")
        self.assertEqual(self.anonymous.get(url).status_code, 401)
        invite = self.admin_client.post(url, {
            "email": "owner-e54-http@example.test",
            "company_name": "Horizon E54",
            "sector": "Education",
        }, format="json")
        self.assertEqual(invite.status_code, 200, getattr(invite, "data", None))
        self.assertNotIn("invitation", invite.data["data"])
        self.assertEqual(len(mail.outbox), 1)
        owner_token = self.invitation_token()
        password = self.activate(owner_token, "owner-e54-http@example.test")
        owner = User.objects.get(email="owner-e54-http@example.test")
        company = Enterprise.objects.get(user=owner)
        self.assertIsNotNone(company.verified_at)

        owner_client = self.login_with_mfa(owner.email, password)
        owner_dashboard = owner_client.get(reverse("enterprise-dashboard-e53"))
        self.assertEqual(owner_dashboard.status_code, 200)
        self.assertEqual(owner_dashboard.data["data"]["membership"], "owner")
        self.assertEqual(owner_dashboard.data["data"]["company"]["id"], company.pk)

        recruiter_invite = owner_client.post(reverse("enterprise-recruiter-invitations"), {
            "email": "recruiter-e54-http@example.test",
        }, format="json")
        self.assertEqual(recruiter_invite.status_code, 200, getattr(recruiter_invite, "data", None))
        self.assertEqual(len(mail.outbox), 2)
        recruit_token = self.invitation_token()
        recruiter_password = self.activate(recruit_token, "recruiter-e54-http@example.test")
        recruiter = User.objects.get(email="recruiter-e54-http@example.test")
        member = EnterpriseMember.objects.get(user=recruiter, enterprise=company)

        recruiter_client = self.login_with_mfa(recruiter.email, recruiter_password)
        self.assertEqual(recruiter_client.get(reverse("enterprise-dashboard-e53")).data["data"]["membership"], "recruiter")
        self.assertEqual(recruiter_client.get(reverse("enterprise-offers")).status_code, 200)
        self.assertEqual(recruiter_client.get(reverse("subscription-my")).status_code, 403)
        self.assertEqual(recruiter_client.post(reverse("enterprise-recruiter-invitations"), {
            "email": "other@example.test",
        }, format="json").status_code, 403)
        self.assertEqual(recruiter_client.post(
            reverse("web-resume"), {"role": "enterprise"}, format="json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
        ).status_code, 200)

        revoke = owner_client.post(reverse("enterprise-recruiter-revoke", args=[member.pk]), {}, format="json")
        self.assertEqual(revoke.status_code, 200)
        self.assertEqual(recruiter_client.get(reverse("enterprise-dashboard-e53")).status_code, 401)
        self.assertEqual(recruiter_client.post(
            reverse("web-resume"), {"role": "enterprise"}, format="json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
        ).status_code, 401)
        self.assertEqual(owner_client.get(reverse("enterprise-dashboard-e53")).status_code, 200)

    def test_admin_can_revoke_owner_invitation_before_activation(self):
        invited = self.admin_client.post(reverse("admin-enterprise-invitations"), {
            "email": "revoked-e54-http@example.test", "company_name": "Disabled", "sector": "IT",
        }, format="json")
        self.assertEqual(invited.status_code, 200)
        token = self.invitation_token()
        response = self.admin_client.post(
            reverse("enterprise-invitation-revoke", args=[invited.data["data"]["id"]]), {},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.anonymous.post(
            reverse("enterprise-invitation-preview"), {"invitation": token}, format="json",
        ).status_code, 400)
        self.assertFalse(User.objects.filter(email="revoked-e54-http@example.test").exists())


@override_settings(DEBUG=False, GCONNECT_WEB_APP_URL="https://portal.example.test")
class ProductionInvitationEmailConfigE54Tests(TestCase):
    def test_non_delivering_email_backends_are_rejected(self):
        from .enterprise_views import _mail_is_ready
        for backend in (
            "django.core.mail.backends.console.EmailBackend",
            "django.core.mail.backends.dummy.EmailBackend",
            "django.core.mail.backends.locmem.EmailBackend",
            "django.core.mail.backends.filebased.EmailBackend",
        ):
            with self.subTest(backend=backend), override_settings(EMAIL_BACKEND=backend):
                self.assertIsNone(_mail_is_ready())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    def test_production_email_requires_https_app_origin(self):
        from .enterprise_views import _mail_is_ready
        self.assertEqual(_mail_is_ready(), "https://portal.example.test")
        with override_settings(GCONNECT_WEB_APP_URL="http://portal.example.test"):
            self.assertIsNone(_mail_is_ready())
        with override_settings(GCONNECT_WEB_APP_URL=""):
            self.assertIsNone(_mail_is_ready())
