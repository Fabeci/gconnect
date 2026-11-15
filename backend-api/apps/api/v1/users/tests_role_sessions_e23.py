"""Regression: one browser may keep three independently MFA-verified portals."""
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, InstitutionAdmin, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from apps.api.v1.users.web_authentication import ROLE_COOKIE_NAMES, set_web_session_cookie
from apps.api.v1.users.web_views import EstablishmentWebResumeView


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
class ProfessionalRoleSessionTests(TestCase):
    def test_three_role_cookies_survive_each_others_logins(self):
        factory = APIRequestFactory()
        institution = Institution.objects.create(name="Session School", acronym="RS")
        users = {}
        values = {}
        for role in ("superAdmin", "etablissement", "enterprise"):
            user = User.objects.create_user(
                username="test_" + role, email=role + "@session.example.test",
                password="Isolated-Role-Session-Test!", role=role, is_active=True,
            )
            if role == "etablissement":
                InstitutionAdmin.objects.create(user=user, institution=institution)
            if role == "enterprise":
                Enterprise.objects.create(verified_at=timezone.now(), user=user, company_name="Session Company", sector="Tech")
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
            session, raw = EstablishmentWebSession.issue(user, factory.post("/"))
            response = set_web_session_cookie(
                HttpResponse(), raw, factory.post("/"), session.expires_at, role,
            )
            users[role] = user
            values[ROLE_COOKIE_NAMES[role]] = response.cookies[ROLE_COOKIE_NAMES[role]].value
            # The legacy cookie is intentionally overwritten by the next login.
            values["gconnect_web_session"] = response.cookies["gconnect_web_session"].value

        cookies = "; ".join(name + "=" + value for name, value in values.items())
        for role, expected in users.items():
            request = factory.post(
                "/api/v1/users/web-resume/", {"role": role}, format="json",
                HTTP_ORIGIN="http://localhost:5173", HTTP_COOKIE=cookies,
            )
            result = EstablishmentWebResumeView.as_view()(request)
            self.assertEqual(result.status_code, 200, (role, result.data))
            self.assertEqual(result.data["data"]["role"], expected.role)

    def test_role_cookie_does_not_authenticate_other_role(self):
        factory = APIRequestFactory()
        user = User.objects.create_user(
            username="other_role", email="other_role@session.example.test",
            password="Isolated-Role-Session-Test!", role="superAdmin", is_active=True,
        )
        PrivilegedMFADevice.objects.create(
            user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
            confirmed_at=timezone.now(),
        )
        _, raw = EstablishmentWebSession.issue(user, factory.post("/"))
        request = factory.post(
            "/api/v1/users/web-resume/", {"role": "etablissement"}, format="json",
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_COOKIE="gconnect_web_session_etablissement=" + raw,
        )
        result = EstablishmentWebResumeView.as_view()(request)
        self.assertEqual(result.status_code, 401)
