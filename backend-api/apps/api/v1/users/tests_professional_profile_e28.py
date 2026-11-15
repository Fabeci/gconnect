"""E28 professional accounts: MFA-bound avatar + settings, no role escalation."""
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, InstitutionAdmin, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from apps.api.v1.users.professional_profile_views import ProfessionalProfileView


def image_file():
    buffer = BytesIO()
    Image.new("RGB", (18, 18), color=(35, 90, 230)).save(buffer, format="PNG")
    return SimpleUploadedFile("avatar.png", buffer.getvalue(), content_type="image/png")


class ProfessionalProfileE28Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.tmp.name)
        self.media.enable()
        self.addCleanup(self.media.disable)
        self.admin = User.objects.create_user(
            username="profile-admin", email="profile-admin@example.test",
            password="password-test-ABC", role="superAdmin", is_active=True,
        )
        self.company_user = User.objects.create_user(
            username="profile-company", email="profile-company@example.test",
            password="password-test-ABC", role="enterprise", is_active=True,
        )
        self.school_user = User.objects.create_user(
            username="profile-school", email="profile-school@example.test",
            password="password-test-ABC", role="etablissement", is_active=True,
        )
        self.company = Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.company_user, company_name="Profile Company", sector="IT",
        )
        self.school = Institution.objects.create(name="Profile School")
        InstitutionAdmin.objects.create(user=self.school_user, institution=self.school)
        self.tokens = {}
        for user in (self.admin, self.company_user, self.school_user):
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
            _, token = EstablishmentWebSession.issue(user, self.factory.get("/"))
            self.tokens[user.pk] = token

    def call(self, user, method="get", data=None):
        headers = {"HTTP_AUTHORIZATION": "WebToken " + self.tokens[user.pk]}
        request = (
            self.factory.patch("/api/v1/users/web-profile/", data or {}, format="multipart", **headers)
            if method == "patch"
            else self.factory.get("/api/v1/users/web-profile/", **headers)
        )
        return ProfessionalProfileView.as_view()(request)

    def test_each_professional_can_view_only_own_identity(self):
        for user in (self.admin, self.company_user, self.school_user):
            response = self.call(user)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["data"]["email"], user.email)
            self.assertEqual(response.data["data"]["role"], user.role)

    def test_unauthenticated_request_refused(self):
        response = ProfessionalProfileView.as_view()(self.factory.get("/api/v1/users/web-profile/"))
        self.assertEqual(response.status_code, 401)

    def test_photo_persists_with_role_and_email_unchanged(self):
        response = self.call(self.company_user, "patch", {
            "photo": image_file(), "first_name": "Anne", "last_name": "Barry",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/avatars/", response.data["data"]["photo_url"])
        self.company_user.refresh_from_db()
        self.assertTrue(self.company_user.photo.name.startswith("avatars/"))
        self.assertEqual(self.company_user.role, "enterprise")
        self.assertEqual(self.company_user.email, "profile-company@example.test")
        own = self.call(self.company_user)
        self.assertEqual(own.data["data"]["full_name"], "Anne Barry")
        self.assertIsNone(self.call(self.school_user).data["data"]["photo_url"])

    def test_reject_invalid_photo_and_oversized_fields(self):
        bad = SimpleUploadedFile("unsafe.jpg", b"not a real image", content_type="image/jpeg")
        self.assertEqual(self.call(self.admin, "patch", {"photo": bad}).status_code, 400)
        self.assertEqual(self.call(self.school_user, "patch", {
            "first_name": "A" * 151,
        }).status_code, 400)

    def test_photo_removal_does_not_affect_other_user(self):
        self.assertEqual(self.call(self.admin, "patch", {"photo": image_file()}).status_code, 200)
        self.assertEqual(self.call(self.school_user, "patch", {"photo": image_file()}).status_code, 200)
        self.assertEqual(self.call(self.admin, "patch", {"remove_photo": "true"}).status_code, 200)
        self.admin.refresh_from_db()
        self.school_user.refresh_from_db()
        self.assertFalse(self.admin.photo)
        self.assertTrue(self.school_user.photo)
        self.assertFalse(self.call(self.admin).data["data"]["photo_url"])
        self.assertTrue(self.call(self.school_user).data["data"]["photo_url"])

    def test_ignores_privilege_mutation_fields(self):
        result = self.call(self.company_user, "patch", {
            "first_name": "Test", "role": "superAdmin",
            "email": "changed@example.test",
        })
        self.assertEqual(result.status_code, 200)
        self.company_user.refresh_from_db()
        self.assertEqual(self.company_user.role, "enterprise")
        self.assertEqual(self.company_user.email, "profile-company@example.test")
