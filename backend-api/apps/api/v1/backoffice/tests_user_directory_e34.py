"""E34 · Répertoire utilisateur: vraie source, accès MFA, moindre exposition."""
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.api.v1.backoffice.user_directory_e34 import SuperadminUserDirectoryE34
from apps.api.v1.users.models import (
    User, Enterprise, PrivilegedMFADevice, EstablishmentWebSession,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class SuperadminUserDirectoryE34Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e34admin", email="e34-admin@example.test",
            role="superAdmin", password="A-long-test-password!", is_active=True,
        )
        cls.enterprise_user = User.objects.create_user(
            username="e34company", email="e34company@example.test",
            role="enterprise", password="A-long-test-password!", is_active=True,
            first_name="Mame", last_name="Diarra", location="Dakar",
        )
        Enterprise.objects.create(
            verified_at=timezone.now(),
            user=cls.enterprise_user, company_name="Entreprise Horizon", sector="Services",
        )
        cls.student = User.objects.create_user(
            username="e34student", email="e34student@example.test",
            role="student", password="A-long-test-password!", is_active=True,
        )
        cls.alumni = User.objects.create_user(
            username="e34alumni", email="e34alumni@example.test",
            role="alumni", password="A-long-test-password!", is_active=False,
        )
        cls.banned = User.objects.create_user(
            username="e34banned", email="e34banned@example.test",
            role="etablissement", password="A-long-test-password!", is_active=True,
            is_banned=True,
        )
        for user in (cls.admin, cls.enterprise_user):
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )

    def setUp(self):
        self.factory = APIRequestFactory()
        _, self.token = EstablishmentWebSession.issue(
            self.admin, self.factory.get("/"),
        )
        _, self.company_token = EstablishmentWebSession.issue(
            self.enterprise_user, self.factory.get("/"),
        )

    def get(self, params=None, who="admin"):
        headers = {}
        if who != "anonymous":
            token = self.token if who == "admin" else self.company_token
            headers["HTTP_AUTHORIZATION"] = "WebToken " + token
        return SuperadminUserDirectoryE34.as_view()(
            self.factory.get("/api/v1/backoffice/user-directory/", params or {}, **headers),
        )

    def test_access_requires_verified_superadmin_session(self):
        self.assertEqual(self.get(who="anonymous").status_code, 401)
        self.assertEqual(self.get(who="enterprise").status_code, 403)

    def test_actual_counts_real_roles_and_minimal_personal_data(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        payload = response.data["data"]
        self.assertEqual(payload["count"], 5)
        self.assertEqual(payload["summary"]["total"], 5)
        self.assertEqual(payload["summary"]["active"], 3)
        self.assertEqual(payload["summary"]["pending"], 1)
        self.assertEqual(payload["summary"]["banned"], 1)
        self.assertEqual(payload["summary"]["students"], 1)
        self.assertEqual(payload["summary"]["alumni"], 1)
        self.assertEqual(payload["summary"]["enterprises"], 1)
        self.assertEqual(payload["summary"]["superadmins"], 1)
        self.assertEqual(payload["summary"]["institution_admins"], 1)
        roles = [item["value"] for item in payload["roles"]]
        self.assertNotIn("recruteur", roles)
        self.assertEqual(set(roles), {"student", "alumni", "enterprise", "etablissement", "superAdmin"})
        company = next(u for u in payload["results"] if u["role"] == "enterprise")
        self.assertEqual(company["association"], "Entreprise Horizon")
        self.assertEqual(company["display_name"], "Mame Diarra")
        self.assertNotIn("password", company)
        self.assertNotIn("token", company)
        self.assertNotIn("phone_number", company)
        self.assertNotIn("date_of_birth", company)
        self.assertNotIn("photo_url", company)

    def test_search_role_status_and_pagination(self):
        self.assertEqual(self.get({"search": "Mame"}).data["data"]["count"], 1)
        self.assertEqual(self.get({"search": "Dakar"}).data["data"]["count"], 1)
        self.assertEqual(self.get({"role": "student"}).data["data"]["count"], 1)
        self.assertEqual(self.get({"role": "alumni", "status": "pending"}).data["data"]["count"], 1)
        self.assertEqual(self.get({"status": "active"}).data["data"]["count"], 3)
        self.assertEqual(self.get({"status": "banned"}).data["data"]["count"], 1)
        filtered = self.get({"role": "enterprise"}).data["data"]
        self.assertEqual(filtered["count"], 1)
        self.assertEqual(filtered["summary"]["total"], 5)
        page = self.get({"page": 2, "page_size": 2}).data["data"]
        self.assertEqual(page["pages"], 3)
        self.assertEqual(len(page["results"]), 2)

    def test_bad_filters_and_pagination_refused(self):
        self.assertEqual(self.get({"role": "recruteur"}).status_code, 400)
        self.assertEqual(self.get({"status": "unknown"}).status_code, 400)
        self.assertEqual(self.get({"page": "-1"}).status_code, 400)
        self.assertEqual(self.get({"page_size": 99}).status_code, 400)
        self.assertEqual(self.get({"page": "NaN"}).status_code, 400)
        self.assertEqual(self.get({"page": 999}).status_code, 404)
