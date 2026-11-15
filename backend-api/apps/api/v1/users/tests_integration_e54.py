"""HTTP regressions at the E38/E53 boundary; no mocked authentication."""
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.v1.publicapi.models import ApiKey
from .models import Enterprise, EnterpriseMember, EstablishmentWebSession, PrivilegedMFADevice, User
from .privileged_security import encrypt_totp, generate_totp_secret
from .web_authentication import ROLE_COOKIE_NAMES


@override_settings(CORS_ALLOWED_ORIGINS=["https://portal.example.test"])
class IntegrationE54Tests(TestCase):
    def setUp(self):
        self.owner = self.person("owner")
        self.company = Enterprise.objects.create(
            user=self.owner, company_name="E38 Company", sector="IT",
            verified_at=timezone.now(),
        )
        self.recruiter = self.person("recruiter")
        self.member = EnterpriseMember.objects.create(user=self.recruiter, enterprise=self.company)
        self.owner_client, self.owner_raw = self.client_for(self.owner)
        self.recruiter_client, self.recruiter_raw = self.client_for(self.recruiter)

    def person(self, name):
        user = User.objects.create_user(
            username="e54_" + name, email=name + "@e54.example.test",
            password="Strong-E54-Integration!", role="enterprise", is_active=True,
        )
        PrivilegedMFADevice.objects.create(
            user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
            confirmed_at=timezone.now(),
        )
        return user

    def client_for(self, user):
        _, raw = EstablishmentWebSession.issue(user, APIRequestFactory().post("/"))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="WebToken " + raw)
        client.cookies[ROLE_COOKIE_NAMES["enterprise"]] = raw
        return client, raw

    def resume(self, client):
        return client.post(reverse("web-resume"), {"role": "enterprise"}, format="json",
                           HTTP_ORIGIN="https://portal.example.test")

    def test_owner_and_recruiter_routes_keep_company_identity_and_profile(self):
        for client, membership in ((self.owner_client, "owner"), (self.recruiter_client, "recruiter")):
            me = client.get(reverse("me"))
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.data["data"]["company_name"], self.company.company_name)
            self.assertEqual(me.data["data"]["enterprise_id"], self.company.pk)
            self.assertEqual(me.data["data"]["enterprise_role"], membership)
            self.assertEqual(client.get(reverse("web-professional-profile")).status_code, 200)
            dashboard = client.get(reverse("enterprise-dashboard-e53"))
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.data["data"]["membership"], membership)
            self.assertEqual(client.get(reverse("enterprise-offers")).status_code, 200)

    def test_recruiter_cannot_take_over_e38_billing(self):
        for name in ("subscription-my", "subscription-change-requests-my"):
            with self.subTest(route=name):
                self.assertEqual(self.owner_client.get(reverse(name)).status_code, 200)
                self.assertEqual(self.recruiter_client.get(reverse(name)).status_code, 403)
        self.assertEqual(self.recruiter_client.post(reverse("subscription-checkout-start"), {}, format="json").status_code, 403)
        invoices = self.recruiter_client.get(reverse("e38-my-invoices"))
        self.assertEqual(invoices.status_code, 200)
        self.assertEqual(invoices.data["data"]["count"], 0)

    def test_recruiter_cookie_resume_stops_after_revocation_owner_survives(self):
        resumed = self.resume(self.recruiter_client)
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.data["data"]["token"], self.recruiter_raw)
        revoked = self.owner_client.post(reverse("enterprise-recruiter-revoke", args=[self.member.pk]))
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(self.resume(self.recruiter_client).status_code, 401)
        self.assertEqual(self.resume(self.owner_client).status_code, 200)
        self.assertEqual(self.recruiter_client.get(reverse("web-professional-profile")).status_code, 401)

    def test_company_deactivation_invalidates_owner_and_recruiter_cookies(self):
        self.company.is_active = False
        self.company.save(update_fields=["is_active"])
        for client in (self.owner_client, self.recruiter_client):
            self.assertEqual(self.resume(client).status_code, 401)

    def test_company_api_key_cannot_bypass_mfa(self):
        _, raw = ApiKey.generate(self.owner, "E54 test")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="ApiKey " + raw)
        self.assertEqual(client.get(reverse("me")).status_code, 401)

    def test_legacy_upgrade_preserves_credentials_and_existing_session(self):
        self.company.verified_at = None
        self.company.save(update_fields=["verified_at"])
        password = self.owner.password
        secret = self.owner.privileged_mfa.encrypted_secret
        session = EstablishmentWebSession.objects.get(user=self.owner)
        digest, expiry = session.token_hash, session.expires_at
        migrate = import_module("apps.api.v1.users.migrations.0014_preserve_e38_enterprise_access")
        migrate.preserve_existing_companies(apps, SimpleNamespace(connection=connection))
        self.company.refresh_from_db()
        verified = self.company.verified_at
        self.assertIsNotNone(verified)
        migrate.preserve_existing_companies(apps, SimpleNamespace(connection=connection))
        self.company.refresh_from_db()
        self.owner.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(self.company.verified_at, verified)
        self.assertEqual(self.owner.password, password)
        self.assertEqual(self.owner.privileged_mfa.encrypted_secret, secret)
        self.assertEqual((session.token_hash, session.expires_at), (digest, expiry))
        self.assertIsNone(session.revoked_at)
        self.assertEqual(self.resume(self.owner_client).status_code, 200)

    def test_post_upgrade_company_is_not_automatically_verified(self):
        user = self.person("uninvited")
        company = Enterprise.objects.create(user=user, company_name="Uninvited", sector="IT")
        self.assertIsNone(company.verified_at)
        client, _ = self.client_for(user)
        self.assertEqual(self.resume(client).status_code, 401)
