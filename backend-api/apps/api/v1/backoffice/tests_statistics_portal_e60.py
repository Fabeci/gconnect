"""E60: real aggregate analytics, period alignment and MFA-only privilege."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.v1.backoffice.models import Report
from apps.api.v1.establishments.models import Institution
from apps.api.v1.posts.models import Post
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class StatisticsE60Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e60admin", email="e60admin@example.test",
            password="Strong-e60-admin!", role="superAdmin", is_active=True,
        )
        cls.owner = User.objects.create_user(
            username="e60enterprise", email="e60enterprise@example.test",
            password="Strong-e60-owner!", role="enterprise", is_active=True,
        )
        cls.student = User.objects.create_user(
            username="e60student", email="e60student@example.test",
            password="Strong-e60-student!", role="student", is_active=True,
        )
        cls.alumni = User.objects.create_user(
            username="e60alumni", email="e60alumni@example.test",
            password="Strong-e60-alumni!", role="alumni", is_active=True,
        )
        User.objects.filter(pk=cls.alumni.pk).update(
            date_joined=timezone.now() - timedelta(days=45),
        )
        cls.company = Enterprise.objects.create(
            user=cls.owner, company_name="Horizon E60", sector="Tech",
            is_active=True, verified_at=timezone.now(),
        )
        cls.institution = Institution.objects.create(
            name="Campus E60", is_active=True,
        )
        cls.post = Post.objects.create(
            author=cls.owner, title="Annonce vérifiée E60",
            post_type=Post.PostType.OPPORTUNITY, content="Données de test",
        )
        Post.objects.create(
            author=cls.student, title="Événement E60",
            post_type=Post.PostType.EVENT,
        )
        Report.objects.create(
            reporter=cls.student, post=cls.post, reason=Report.Reason.SPAM,
        )
        for user in (cls.admin, cls.owner):
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )

    def setUp(self):
        req = APIRequestFactory().get("/")
        _, token = EstablishmentWebSession.issue(self.admin, req)
        _, enterprise_token = EstablishmentWebSession.issue(self.owner, req)
        self.client_admin = APIClient()
        self.client_admin.credentials(HTTP_AUTHORIZATION="WebToken " + token)
        self.client_enterprise = APIClient()
        self.client_enterprise.credentials(HTTP_AUTHORIZATION="WebToken " + enterprise_token)
        self.guest = APIClient()
        self.url = reverse("superadmin-statistics-e60")

    def test_mfa_and_superadmin_only(self):
        self.assertEqual(self.guest.get(self.url).status_code, 401)
        self.assertEqual(self.client_enterprise.get(self.url).status_code, 403)

    def test_real_global_totals_and_provenance_without_personal_data(self):
        response = self.client_admin.get(self.url, {"days": 30})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store")
        data = response.data["data"]
        self.assertEqual(data["summary"]["accounts_total"], 4)
        self.assertEqual(data["summary"]["accounts_active"], 4)
        self.assertEqual(data["summary"]["new_accounts"], 3)
        self.assertEqual(data["summary"]["previous_accounts"], 1)
        self.assertEqual(data["summary"]["growth_percent"], 200.0)
        self.assertEqual(data["summary"]["enterprises_total"], 1)
        self.assertEqual(data["summary"]["enterprises_verified"], 1)
        self.assertEqual(data["summary"]["institutions_active"], 1)
        self.assertEqual(data["summary"]["posts_total"], 2)
        self.assertEqual(data["summary"]["posts_published"], 2)
        self.assertEqual(data["summary"]["reports_pending"], 1)
        self.assertEqual(data["roles"]["student"], 1)
        self.assertEqual(data["roles"]["alumni"], 1)
        self.assertEqual(data["roles"]["enterprise"], 1)
        self.assertEqual(data["roles"]["superAdmin"], 1)
        self.assertEqual(data["contents"]["opportunity"], 1)
        self.assertEqual(data["contents"]["event"], 1)
        self.assertEqual(data["sources"]["enterprise_accounts"], "Enterprise.user.date_joined")
        self.assertEqual(len(data["trend"]["labels"]), 30)
        self.assertEqual(sum(data["trend"]["accounts"]), 3)
        self.assertEqual(sum(data["trend"]["posts"]), 2)
        self.assertEqual(sum(data["trend"]["institutions"]), 1)
        self.assertEqual(sum(data["trend"]["enterprise_accounts"]), 1)
        serialized = str(data)
        for secret in ("e60student@example.test", "password", "token", "phone_number", "resume"):
            self.assertNotIn(secret, serialized)

    def test_date_granularities_are_bounded_and_series_are_aligned(self):
        for days, grain in ((30, "day"), (90, "week"), (180, "month"), (365, "month")):
            response = self.client_admin.get(self.url, {"days": days})
            self.assertEqual(response.status_code, 200, response.data)
            data = response.data["data"]
            self.assertEqual(data["granularity"], grain)
            labels = data["trend"]["labels"]
            self.assertGreaterEqual(len(labels), 4)
            self.assertLessEqual(len(labels), 31)
            self.assertEqual(labels, sorted(labels))
            for key in ("accounts", "posts", "institutions", "enterprise_accounts"):
                self.assertEqual(len(data["trend"][key]), len(labels))
                self.assertTrue(all(isinstance(value, int) and value >= 0 for value in data["trend"][key]))
            self.assertEqual(sum(data["trend"]["posts"]), 2)

    def test_invalid_period_is_rejected(self):
        for value in ("", "0", "29", "31", "99999", "x", "-30", "1.5"):
            self.assertEqual(
                self.client_admin.get(self.url, {"days": value}).status_code, 400,
                value,
            )

    def test_missing_comparison_baseline_is_null_not_fabricated_growth(self):
        self.alumni.date_joined = timezone.now()
        self.alumni.save(update_fields=["date_joined"])
        response = self.client_admin.get(self.url, {"days": 30})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["data"]["summary"]["growth_percent"])
        self.assertEqual(response.data["data"]["summary"]["previous_accounts"], 0)

    def test_role_and_status_counters_are_true_not_percentages_of_total(self):
        User.objects.filter(pk=self.student.pk).update(is_banned=True)
        Institution.objects.filter(pk=self.institution.pk).update(is_active=False)
        Enterprise.objects.filter(pk=self.company.pk).update(is_active=False)
        Post.objects.filter(pk=self.post.pk).update(is_hidden_by_admin=True)
        result = self.client_admin.get(self.url).data["data"]
        self.assertEqual(result["summary"]["accounts_banned"], 1)
        self.assertEqual(result["summary"]["accounts_active"], 3)
        self.assertEqual(result["summary"]["institutions_active"], 0)
        self.assertEqual(result["summary"]["enterprises_verified"], 0)
        self.assertEqual(result["summary"]["posts_hidden"], 1)
        self.assertEqual(result["summary"]["posts_published"], 1)
