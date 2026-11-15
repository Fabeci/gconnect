"""E35 · Security operations guardrails and audit on real Django models."""
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from apps.api.v1.backoffice.user_security_e35 import SuperadminUserSecurityE35
from apps.api.v1.core.models import AuditLogEntry
from apps.api.v1.users.models import (
    User, Enterprise, EstablishmentWebSession, PrivilegedMFADevice,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class UserSecurityE35Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superadmin = User.objects.create_user(
            username="e35super", email="e35-super@example.test",
            role="superAdmin", password="Test-password-e35!", is_active=True,
        )
        cls.other_superadmin = User.objects.create_user(
            username="e35other", email="e35-super2@example.test",
            role="superAdmin", password="Test-password-e35!", is_active=True,
        )
        cls.enterprise = User.objects.create_user(
            username="e35company", email="e35company@example.test",
            role="enterprise", password="Test-password-e35!", is_active=True,
        )
        Enterprise.objects.create(
            verified_at=timezone.now(),
            user=cls.enterprise, company_name="E35 Example", sector="Services",
        )
        cls.student = User.objects.create_user(
            username="e35student", email="e35student@example.test",
            role="student", password="Test-password-e35!", is_active=True,
        )
        cls.pending = User.objects.create_user(
            username="e35pending", email="e35pending@example.test",
            role="alumni", password="Test-password-e35!", is_active=False,
        )
        for actor in (cls.superadmin, cls.other_superadmin, cls.enterprise):
            PrivilegedMFADevice.objects.create(
                user=actor, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )

    def setUp(self):
        self.factory = APIRequestFactory()
        _, self.admin_token = EstablishmentWebSession.issue(
            self.superadmin, self.factory.get("/"),
        )
        _, self.enterprise_token = EstablishmentWebSession.issue(
            self.enterprise, self.factory.get("/"),
        )

    def request(self, pk, action=None, reason="Contrôle antifraude documenté.", who="admin"):
        path = f"/api/v1/backoffice/user-directory/{pk}/security/"
        headers = {}
        if who != "anonymous":
            token = self.admin_token if who == "admin" else self.enterprise_token
            headers["HTTP_AUTHORIZATION"] = "WebToken " + token
        if action is None:
            return SuperadminUserSecurityE35.as_view()(self.factory.get(path, **headers), pk=pk)
        return SuperadminUserSecurityE35.as_view()(
            self.factory.post(path, {"action": action, "reason": reason}, format="json", **headers),
            pk=pk,
        )

    def test_only_verified_superadmin_can_read_and_modify(self):
        self.assertEqual(self.request(self.student.pk, who="anonymous").status_code, 401)
        self.assertEqual(self.request(self.student.pk, who="enterprise").status_code, 403)
        self.assertEqual(self.request(self.student.pk, action="ban", who="anonymous").status_code, 401)
        self.assertEqual(self.request(self.student.pk, action="ban", who="enterprise").status_code, 403)
        self.assertEqual(self.request(999999).status_code, 404)

    def test_security_summary_and_role_protection(self):
        details = self.request(self.enterprise.pk)
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details["Cache-Control"], "no-store")
        data = details.data["data"]
        self.assertEqual(data["eligible_actions"], ["ban", "revoke_sessions"])
        self.assertEqual(data["history"], [])
        self.assertNotIn("token", data)
        self.assertNotIn("mfa_secret", data)
        self.assertEqual(self.request(self.superadmin.pk).data["data"]["eligible_actions"], [])
        self.assertEqual(self.request(self.other_superadmin.pk).data["data"]["eligible_actions"], [])
        for account in (self.superadmin, self.other_superadmin):
            self.assertEqual(self.request(account.pk, action="ban").status_code, 403)
            self.assertEqual(self.request(account.pk, action="revoke_sessions").status_code, 403)
        self.assertFalse(AuditLogEntry.objects.filter(action="user_banned").exists())

    def test_ban_forces_web_and_mobile_reauthentication_and_audits_reason(self):
        _, extra = EstablishmentWebSession.issue(self.enterprise, self.factory.get("/"))
        mobile_token, _ = Token.objects.get_or_create(user=self.enterprise)
        self.assertTrue(mobile_token.key)
        decision = self.request(self.enterprise.pk, action="ban", reason="Alerte fraude vérifiée sur compte.")
        self.assertEqual(decision.status_code, 200)
        self.enterprise.refresh_from_db()
        self.assertTrue(self.enterprise.is_banned)
        self.assertEqual(self.enterprise.banned_reason, "Alerte fraude vérifiée sur compte.")
        self.assertEqual(decision.data["data"]["web_sessions_revoked"], 2)
        self.assertFalse(Token.objects.filter(user=self.enterprise).exists())
        self.assertEqual(EstablishmentWebSession.objects.filter(user=self.enterprise, revoked_at__isnull=True).count(), 0)
        event = AuditLogEntry.objects.get(action="user_banned")
        self.assertEqual(event.user_id, self.superadmin.pk)
        self.assertEqual(event.metadata["target_user_id"], self.enterprise.pk)
        self.assertEqual(event.metadata["reason"], "Alerte fraude vérifiée sur compte.")
        history = self.request(self.enterprise.pk).data["data"]
        self.assertEqual(history["eligible_actions"], ["unban"])
        self.assertEqual(history["history"][0]["action"], "user_banned")
        self.assertEqual(history["history"][0]["reason"], event.metadata["reason"])
        self.assertEqual(history["live_web_sessions"], 0)

    def test_unban_preserves_activation_and_records_decision(self):
        self.request(self.pending.pk, action="ban", reason="Suspicion contrôlée par équipe.")
        decision = self.request(self.pending.pk, action="unban", reason="Vérifications terminées et validées.")
        self.assertEqual(decision.status_code, 200)
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.is_banned)
        self.assertFalse(self.pending.is_active, "Unbanning cannot circumvent activation workflow")
        self.assertEqual(self.pending.banned_reason, "")
        self.assertIsNone(self.pending.banned_at)
        self.assertEqual(AuditLogEntry.objects.filter(action="user_unbanned").count(), 1)
        self.assertEqual(self.request(self.pending.pk).data["data"]["eligible_actions"],
                         ["ban", "revoke_sessions"])

    def test_revoke_sessions_without_banning_account(self):
        Token.objects.get_or_create(user=self.enterprise)
        _, _ = EstablishmentWebSession.issue(self.enterprise, self.factory.get("/"))
        result = self.request(self.enterprise.pk, action="revoke_sessions",
                              reason="Déconnexion des appareils demandée.")
        self.assertEqual(result.status_code, 200)
        self.enterprise.refresh_from_db()
        self.assertFalse(self.enterprise.is_banned)
        self.assertTrue(self.enterprise.is_active)
        self.assertFalse(Token.objects.filter(user=self.enterprise).exists())
        self.assertEqual(EstablishmentWebSession.objects.filter(
            user=self.enterprise, revoked_at__isnull=True).count(), 0)
        self.assertEqual(AuditLogEntry.objects.get(action="sessions_revoked").metadata["target_user_id"],
                         self.enterprise.pk)
        self.assertEqual(self.request(self.enterprise.pk).data["data"]["history"][0]["action"],
                         "sessions_revoked")

    def test_invalid_reason_actions_and_conflicts_do_not_write(self):
        self.assertEqual(self.request(self.student.pk, action="ban", reason="court").status_code, 400)
        self.assertEqual(self.request(self.student.pk, action="ban", reason="").status_code, 400)
        self.assertEqual(self.request(self.student.pk, action="bad_action").status_code, 400)
        self.assertEqual(self.request(self.student.pk, action=[]).status_code, 400)
        self.assertEqual(self.request(self.student.pk, action="unban").status_code, 409)
        self.assertEqual(AuditLogEntry.objects.count(), 0)
        self.assertEqual(self.request(self.student.pk, action="ban").status_code, 200)
        self.assertEqual(self.request(self.student.pk, action="ban").status_code, 409)
        self.assertEqual(self.request(self.student.pk, action="revoke_sessions").status_code, 409)
        self.assertEqual(AuditLogEntry.objects.filter(action="user_banned").count(), 1)
