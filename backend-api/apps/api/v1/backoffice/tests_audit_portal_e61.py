"""E61 regressions: provenance, data minimisation, authentication and pagination."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.v1.core.models import AuditLogEntry
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class AuditE61Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e61admin", email="e61admin@example.test",
            password="Audit-Admin-2026!", role="superAdmin", is_active=True,
            first_name="Alice", last_name="Contrôle",
        )
        cls.company_admin = User.objects.create_user(
            username="e61enterprise", email="e61enterprise@example.test",
            password="Audit-Company-2026!", role="enterprise", is_active=True,
        )
        Enterprise.objects.create(
            user=cls.company_admin, company_name="Groupe E61",
            sector="Services", verified_at=timezone.now(),
        )
        for user in (cls.admin, cls.company_admin):
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
        cls.login = AuditLogEntry.objects.create(
            user=cls.admin, action="login_success", ip_address="192.168.30.24",
            metadata={
                "token": "secret-should-not-be-sent",
                "password": "sensitive-password",
                "refresh": "sensitive-refresh",
                "email": "hidden@example.test",
                "nested": {"password": "secret"},
                "user_id": cls.admin.pk, "total": 2,
                "outcome": "actioned",
                "reason": "Sensitive narrative with private identity",
            },
        )
        cls.invitation = AuditLogEntry.objects.create(
            user=cls.company_admin, action="invitation_sent",
            metadata={"institution_id": 8, "enterprise_id": 2},
        )
        cls.moderation = AuditLogEntry.objects.create(
            user=cls.admin, action="report_reviewed",
            metadata={"report_id": 34, "outcome": "dismissed"},
        )
        cls.operations = AuditLogEntry.objects.create(
            user=cls.admin, action="import_completed",
            metadata={"import_type": "students", "total": 8, "errors": 1},
        )
        cls.other = AuditLogEntry.objects.create(
            user=cls.admin, action="future_action_not_in_enum",
            metadata={"raw": "hidden", "job_id": 2},
        )
        cls.old = AuditLogEntry.objects.create(
            user=cls.admin, action="login_failed",
        )
        AuditLogEntry.objects.filter(pk=cls.old.pk).update(
            created_at=timezone.now() - timedelta(days=200),
        )

    def setUp(self):
        request = APIRequestFactory().get("/")
        _, token = EstablishmentWebSession.issue(self.admin, request)
        _, company_token = EstablishmentWebSession.issue(self.company_admin, request)
        self.owner = APIClient()
        self.owner.credentials(HTTP_AUTHORIZATION="WebToken " + token)
        self.enterprise = APIClient()
        self.enterprise.credentials(HTTP_AUTHORIZATION="WebToken " + company_token)
        self.guest = APIClient()
        self.url = reverse("superadmin-audit-directory-e61")

    def test_only_mfa_superadmin_can_read_register(self):
        self.assertEqual(self.guest.get(self.url).status_code, 401)
        self.assertEqual(self.enterprise.get(self.url).status_code, 403)

    def test_summary_categories_and_real_trend_include_unlisted_actions(self):
        response = self.owner.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store")
        data = response.data["data"]
        summary = data["summary"]
        self.assertEqual(summary["events"], 5)
        self.assertEqual(summary["invitations"], 1)
        self.assertEqual(summary["moderation"], 1)
        self.assertEqual(summary["access"], 1)
        self.assertEqual(summary["operations"], 1)
        self.assertEqual(summary["other"], 1)
        self.assertEqual(summary["failed_access"], 0)
        self.assertEqual(sum(data["trend"]["events"]), 5)
        self.assertEqual(len(data["trend"]["events"]), 30)
        self.assertEqual(data["count"], 5)
        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["results"][-1]["action"], "login_success")

    def test_raw_ip_and_sensitive_metadata_never_leak(self):
        response = self.owner.get(self.url)
        entries = response.data["data"]["results"]
        login = next(row for row in entries if row["id"] == self.login.pk)
        self.assertNotIn("ip_address", login)
        self.assertEqual(login["actor"], "Alice Contrôle")
        self.assertEqual(login["details"], {
            "user_id": self.admin.pk, "total": 2, "outcome": "actioned",
        })
        content = str(response.data)
        for secret in (
            "192.168.30.24", "secret-should-not-be-sent",
            "sensitive-password", "sensitive-refresh", "hidden@example.test",
            "Sensitive narrative with private identity",
        ):
            self.assertNotIn(secret, content)

    def test_category_action_search_and_pagination_filters(self):
        self.assertEqual(
            self.owner.get(self.url, {"category": "invitations"}).data["data"]["count"], 1,
        )
        self.assertEqual(
            self.owner.get(self.url, {"category": "moderation"}).data["data"]["count"], 1,
        )
        self.assertEqual(
            self.owner.get(self.url, {"category": "access"}).data["data"]["count"], 1,
        )
        self.assertEqual(
            self.owner.get(self.url, {"category": "operations"}).data["data"]["count"], 1,
        )
        self.assertEqual(
            self.owner.get(self.url, {"category": "other"}).data["data"]["count"], 1,
        )
        self.assertEqual(
            self.owner.get(self.url, {"action": "report_reviewed"}).data["data"]["count"], 1,
        )
        self.assertEqual(
            self.owner.get(self.url, {"search": "Alice"}).data["data"]["count"], 4,
        )
        self.assertEqual(
            self.owner.get(self.url, {"search": "connexion réussie"}).data["data"]["count"], 1,
        )
        # The all-period counts remain real regardless of the list filters.
        response = self.owner.get(self.url, {"category": "operations"})
        self.assertEqual(response.data["data"]["summary"]["events"], 5)
        # 12 rows per page are supported, not arbitrary unbounded pagination.
        self.assertEqual(response.data["data"]["page_size"], 12)
        self.assertEqual(response.data["data"]["pages"], 1)
        self.assertEqual(response.data["data"]["results"][0]["details"]["total"], 8)

    def test_strict_validation_and_read_only(self):
        before = AuditLogEntry.objects.count()
        for params in (
            {"days": "0"}, {"days": "365"}, {"days": "x"},
            {"page": "-1"}, {"page": "abc"}, {"page_size": "500"},
            {"action": "malicious"}, {"category": "unknown"},
        ):
            self.assertEqual(self.owner.get(self.url, params).status_code, 400, params)
        self.assertEqual(self.owner.get(self.url, {"page": "999"}).status_code, 404)
        self.assertEqual(self.owner.post(self.url, {}, format="json").status_code, 405)
        self.assertEqual(AuditLogEntry.objects.count(), before)

    def test_seven_ninety_and_one_hundred_eighty_days_have_aligned_buckets(self):
        for days,grain in ((7, "day"), (30, "day"), (90, "week"), (180, "month")):
            response = self.owner.get(self.url, {"days": days})
            self.assertEqual(response.status_code, 200, response.data)
            payload = response.data["data"]
            self.assertEqual(payload["trend"]["granularity"], grain)
            self.assertEqual(
                len(payload["trend"]["labels"]), len(payload["trend"]["events"]),
            )
            self.assertEqual(
                sum(payload["trend"]["events"]), payload["summary"]["events"],
            )
            self.assertEqual(payload["count"], 5)
