"""E29: password rotation for three roles through MFA-bound web sessions."""
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import (
    User, Enterprise, InstitutionAdmin, EstablishmentWebSession, PrivilegedMFADevice,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from apps.api.v1.users.professional_password_views import ProfessionalPasswordChangeView


OLD = "Secure-Old-Password-2026!"
NEW = "Very-Secure-New-Password-2026!"


class ProfessionalPasswordE29Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.users = []
        self.tokens = {}
        school = Institution.objects.create(name="E29 School")
        for role in ("superAdmin", "enterprise", "etablissement"):
            user = User.objects.create_user(
                username="e29-" + role, email="e29-" + role + "@example.test",
                password=OLD, role=role, is_active=True,
            )
            if role == "enterprise":
                Enterprise.objects.create(verified_at=timezone.now(), user=user, company_name="E29 Company", sector="IT")
            elif role == "etablissement":
                InstitutionAdmin.objects.create(user=user, institution=school)
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
            _, raw = EstablishmentWebSession.issue(user, self.factory.get("/"))
            self.tokens[user.pk] = raw
            self.users.append(user)

    def change(self, user, current=OLD, new=NEW, auth=True):
        headers = {"HTTP_AUTHORIZATION": "WebToken " + self.tokens[user.pk]} if auth else {}
        req = self.factory.post(
            "/api/v1/users/web-change-password/",
            {"current_password": current, "new_password": new},
            format="json", **headers,
        )
        return ProfessionalPasswordChangeView.as_view()(req)

    def test_success_for_all_three_roles_invalidates_sessions(self):
        for user in self.users:
            other_session, _ = EstablishmentWebSession.issue(user, self.factory.get("/"))
            mobile = Token.objects.create(user=user)
            response = self.change(user)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data["data"]["requires_relogin"])
            user.refresh_from_db()
            self.assertTrue(user.check_password(NEW))
            self.assertFalse(user.check_password(OLD))
            self.assertFalse(EstablishmentWebSession.objects.filter(
                user=user, revoked_at__isnull=True).exists())
            self.assertFalse(Token.objects.filter(pk=mobile.pk).exists())
            self.assertEqual(self.change(user).status_code, 401)

    def test_wrong_password_does_not_change_or_revoke(self):
        user = self.users[0]
        response = self.change(user, "Incorrect!")
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password(OLD))
        self.assertTrue(EstablishmentWebSession.objects.filter(
            user=user, revoked_at__isnull=True).exists())

    def test_same_password_and_weak_new_password_refused(self):
        user = self.users[1]
        self.assertEqual(self.change(user, OLD, OLD).status_code, 400)
        self.assertEqual(self.change(user, OLD, "abc").status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password(OLD))

    def test_anonymous_request_denied(self):
        self.assertEqual(self.change(self.users[2], auth=False).status_code, 401)

    def test_password_change_cannot_modify_other_roles(self):
        admin, company, school = self.users
        self.assertEqual(self.change(company).status_code, 200)
        admin.refresh_from_db()
        school.refresh_from_db()
        self.assertTrue(admin.check_password(OLD))
        self.assertTrue(school.check_password(OLD))
        self.assertTrue(EstablishmentWebSession.objects.filter(
            user=admin, revoked_at__isnull=True).exists())
