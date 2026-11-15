"""E57 regression: Superadmin MFA privilege, true global data and strict read-only filters."""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.v1.backoffice.models import Report
from apps.api.v1.posts.models import Opportunity, Post
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class SuperadminContentDirectoryE57Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e57admin", email="e57admin@example.test",
            password="Test-Password-E57!", role="superAdmin", is_active=True,
        )
        cls.enterprise_user = User.objects.create_user(
            username="e57business", email="e57enterprise@example.test",
            password="Test-Password-E57!", role="enterprise", is_active=True,
            first_name="Awa", last_name="Sow",
        )
        cls.student = User.objects.create_user(
            username="e57student", email="e57student@example.test",
            password="Test-Password-E57!", role="student", is_active=True,
        )
        for person in (cls.admin, cls.enterprise_user):
            PrivilegedMFADevice.objects.create(
                user=person, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
        cls.company = Enterprise.objects.create(
            user=cls.enterprise_user, company_name="Horizon Digital",
            sector="Informatique", verified_at=timezone.now(),
        )
        cls.offer = Post.objects.create(
            author=cls.enterprise_user, title="Ingénieur Backend",
            post_type=Post.PostType.OPPORTUNITY,
            content="Recherche de profils Python.",
        )
        Opportunity.objects.create(
            post=cls.offer, enterprise=cls.company,
            category=Opportunity.Category.JOB, status=Opportunity.Status.OPEN,
        )
        cls.event = Post.objects.create(
            author=cls.student, title="Forum régional",
            post_type=Post.PostType.EVENT, content="Événement pour les diplômés.",
        )
        cls.draft = Post.objects.create(
            author=cls.enterprise_user, title="Brouillon stratégique",
            post_type=Post.PostType.PROJECT, is_draft=True,
        )
        cls.hidden = Post.objects.create(
            author=cls.enterprise_user, title="Message masqué",
            post_type=Post.PostType.DISCUSSION, is_hidden_by_admin=True,
            hidden_reason="Signalement de test",
        )
        cls.archived = Post.objects.create(
            author=cls.student, title="Ancienne annonce",
            post_type=Post.PostType.SHARE, is_archived=True,
        )
        Report.objects.create(
            reporter=cls.student, post=cls.offer,
            reason=Report.Reason.SPAM, status=Report.Status.PENDING,
        )

    def setUp(self):
        req = APIRequestFactory().get("/")
        _, admin_token = EstablishmentWebSession.issue(self.admin, req)
        _, enterprise_token = EstablishmentWebSession.issue(self.enterprise_user, req)
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION="WebToken " + admin_token)
        self.business_client = APIClient()
        self.business_client.credentials(
            HTTP_AUTHORIZATION="WebToken " + enterprise_token,
        )
        self.guest = APIClient()
        self.url = reverse("superadmin-content-directory-e57")

    def test_superadmin_mfa_auth_is_mandatory(self):
        self.assertEqual(self.guest.get(self.url).status_code, 401)
        self.assertEqual(self.business_client.get(self.url).status_code, 403)

    def test_global_counts_are_real_and_no_sensitive_fields_are_returned(self):
        response = self.admin_client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store")
        data = response.data["data"]
        self.assertEqual(data["count"], 5)
        self.assertEqual(data["summary"]["total"], 5)
        self.assertEqual(data["summary"]["opportunities"], 1)
        self.assertEqual(data["summary"]["events"], 1)
        self.assertEqual(data["summary"]["projects"], 1)
        self.assertEqual(data["summary"]["discussions"], 2)
        self.assertEqual(data["summary"]["drafts"], 1)
        self.assertEqual(data["summary"]["hidden"], 1)
        self.assertEqual(data["summary"]["archived"], 1)
        self.assertEqual(data["summary"]["published"], 2)
        self.assertEqual(data["summary"]["reports_pending"], 1)
        offer = next(row for row in data["results"] if row["id"] == self.offer.id)
        self.assertEqual(offer["organisation"], "Horizon Digital")
        self.assertEqual(offer["pending_reports"], 1)
        self.assertEqual(offer["opportunity"]["status"], "open")
        self.assertEqual(offer["author_name"], "Awa Sow")
        for secret in ("email", "password", "token", "mfa", "application_email"):
            self.assertNotIn(secret, offer)

    def test_types_states_search_and_pagination(self):
        self.assertEqual(self.admin_client.get(self.url, {"type": "event"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.url, {"state": "draft"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.url, {"state": "hidden"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.url, {"state": "archived"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.url, {"state": "published"}).data["data"]["count"], 2)
        self.assertEqual(self.admin_client.get(self.url, {"search": "Digital"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.url, {"search": "Forum"}).data["data"]["count"], 1)
        page = self.admin_client.get(self.url, {"page": 2, "page_size": 2}).data["data"]
        self.assertEqual(page["count"], 5)
        self.assertEqual(page["pages"], 3)
        self.assertEqual(len(page["results"]), 2)

    def test_bad_filters_do_not_leak_data(self):
        for params in (
            {"type": "recruteur"}, {"state": "pending"},
            {"page": "0"}, {"page": "abc"}, {"page_size": 100},
        ):
            self.assertEqual(self.admin_client.get(self.url, params).status_code, 400, params)
        self.assertEqual(self.admin_client.get(self.url, {"page": 99}).status_code, 404)
