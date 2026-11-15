"""E62 security posture is real, MFA-only, private and safe from self-revocation."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.v1.core.models import AuditLogEntry
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, LoginAttempt, PrivilegedMFADevice,
    PrivilegedRecoveryCode, User,
)
from apps.api.v1.users.privileged_security import (
    encrypt_totp, generate_totp_secret, token_digest,
)


class SecurityE62Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e62super", email="e62super@example.test",
            role="superAdmin", password="Strong-e62-admin!", is_active=True,
        )
        cls.enterprise = User.objects.create_user(
            username="e62enterprise", email="e62enterprise@example.test",
            role="enterprise", password="Strong-e62-enterprise!", is_active=True,
        )
        cls.pending = User.objects.create_user(
            username="e62pending", email="e62pending@example.test",
            role="enterprise", password="Strong-e62-pending!", is_active=True,
        )
        for target in (cls.enterprise, cls.pending):
            Enterprise.objects.create(
                user=target, company_name="E62 Corp " + target.username,
                sector="Tech", verified_at=timezone.now(),
            )
        for user in (cls.admin, cls.enterprise):
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
        PrivilegedRecoveryCode.objects.create(
            user=cls.admin, code_hash=token_digest("A" * 20),
        )
        PrivilegedRecoveryCode.objects.create(
            user=cls.admin, code_hash=token_digest("B" * 20),
            used_at=timezone.now(),
        )
        LoginAttempt.objects.create(
            email="private-failed@example.test", ip_address="192.168.0.29",
            success=False,
        )
        LoginAttempt.objects.create(
            email="private-success@example.test", ip_address="192.168.0.30",
            success=True,
        )
        LoginAttempt.objects.create(
            email="old@example.test", success=False,
        )
        LoginAttempt.objects.filter(email="old@example.test").update(
            created_at=timezone.now() - timedelta(days=120),
        )

    def setUp(self):
        factory = APIRequestFactory()
        device = factory.get("/", HTTP_USER_AGENT="Mozilla/5.0 Firefox/141.0 Linux X11")
        self.own, token = EstablishmentWebSession.issue(self.admin, device)
        self.other, _ = EstablishmentWebSession.issue(self.admin, device)
        self.foreign, foreign_token = EstablishmentWebSession.issue(
            self.enterprise, factory.get("/", HTTP_USER_AGENT="Bad secret on agent"),
        )
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="WebToken " + token)
        self.not_admin = APIClient()
        self.not_admin.credentials(HTTP_AUTHORIZATION="WebToken " + foreign_token)
        self.guest = APIClient()
        self.url = reverse("superadmin-security-directory-e62")
        self.revoke = lambda pk: reverse(
            "superadmin-security-revoke-session-e62", args=[pk],
        )

    def test_mfa_and_superadmin_authentication_required(self):
        self.assertEqual(self.guest.get(self.url).status_code, 401)
        self.assertEqual(self.not_admin.get(self.url).status_code, 403)
        self.assertEqual(
            self.not_admin.post(self.revoke(self.own.pk), {"confirmation": "REVOQUER"}).status_code, 403,
        )

    def test_real_sessions_mfa_and_attempts_without_sensitive_personal_data(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store")
        data = response.data["data"]
        totals = data["summary"]
        self.assertEqual(totals["sessions_active"], 3)
        self.assertEqual(totals["professionals_active"], 3)
        self.assertEqual(totals["mfa_enabled"], 2)
        self.assertEqual(totals["mfa_pending"], 1)
        self.assertEqual(totals["failures"], 1)
        self.assertEqual(totals["successes"], 1)
        self.assertEqual(data["my_mfa"]["remaining_recovery_codes"], 1)
        self.assertEqual(len(data["my_sessions"]), 2)
        self.assertEqual(sum(row["current"] for row in data["my_sessions"]), 1)
        self.assertEqual(sum(data["trend"]["failures"]), 1)
        self.assertEqual(sum(data["trend"]["successes"]), 1)
        own = next(row for row in data["my_sessions"] if row["current"])
        self.assertEqual(own["device"]["browser"], "Firefox")
        self.assertEqual(own["device"]["os"], "Linux")
        text = str(response.data)
        for value in (
            "private-failed@example.test", "private-success@example.test",
            "192.168.0.29", "192.168.0.30", "Firefox/141.0",
            "Bad secret on agent", "token_hash", "code_hash", "encrypted_secret",
            "e62enterprise@example.test",
        ):
            self.assertNotIn(value, text)

    def test_invalid_period_and_consistent_series(self):
        for days in ("", "0", "1", "365", "xyz", "-7"):
            self.assertEqual(self.client.get(self.url, {"days": days}).status_code, 400)
        for days, grain in ((7, "day"), (30, "day"), (90, "week")):
            response = self.client.get(self.url, {"days": days})
            self.assertEqual(response.status_code, 200)
            data = response.data["data"]
            self.assertEqual(data["trend"]["granularity"], grain)
            self.assertEqual(len(data["trend"]["labels"]), len(data["trend"]["successes"]))
            self.assertEqual(len(data["trend"]["labels"]), len(data["trend"]["failures"]))
            self.assertEqual(sum(data["trend"]["failures"]), data["summary"]["failures"])

    def test_revoke_requires_confirmation_and_cannot_revoke_current_or_foreign(self):
        self.assertEqual(
            self.client.post(self.revoke(self.other.pk), {}, format="json").status_code, 400,
        )
        self.assertEqual(
            self.client.post(self.revoke(self.own.pk), {"confirmation": "REVOQUER"}, format="json").status_code, 409,
        )
        self.assertEqual(
            self.client.post(self.revoke(self.foreign.pk), {"confirmation": "REVOQUER"}, format="json").status_code, 404,
        )
        self.own.refresh_from_db()
        self.other.refresh_from_db()
        self.assertIsNone(self.own.revoked_at)
        self.assertIsNone(self.other.revoked_at)

    def test_revoke_other_session_is_attributed_and_not_repeatable(self):
        before = AuditLogEntry.objects.filter(action="sessions_revoked").count()
        response = self.client.post(
            self.revoke(self.other.pk), {"confirmation": "REVOQUER"}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.other.refresh_from_db()
        self.own.refresh_from_db()
        self.assertIsNotNone(self.other.revoked_at)
        self.assertIsNone(self.own.revoked_at)
        self.assertEqual(
            self.client.post(self.revoke(self.other.pk), {"confirmation": "REVOQUER"}, format="json").status_code,
            409,
        )
        self.assertEqual(AuditLogEntry.objects.filter(action="sessions_revoked").count(), before + 1)
        event = AuditLogEntry.objects.filter(action="sessions_revoked").latest("id")
        self.assertEqual(event.user_id, self.admin.pk)
        self.assertEqual(event.metadata["session_id"], self.other.pk)
        self.assertEqual(event.metadata["source"], "superadmin_sessions_e62")
        self.assertEqual(len(self.client.get(self.url).data["data"]["my_sessions"]), 1)
