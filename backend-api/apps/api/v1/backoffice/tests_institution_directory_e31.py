"""E31 secured directory: actual data, pagination, search and MFA role isolation."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.api.v1.backoffice.institution_directory_e31 import SuperadminInstitutionDirectoryE31
from apps.api.v1.establishments.models import Institution, StudentInstitution, AlumniInstitution
from apps.api.v1.subscriptions.models import CommercialOffer, PriceOption, BusinessSubscription
from apps.api.v1.users.models import User, Enterprise, PrivilegedMFADevice, EstablishmentWebSession
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class InstitutionDirectoryE31Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e31admin", email="e31admin@example.test",
            password="Password-Of-Tests-123!", role="superAdmin", is_active=True,
        )
        cls.other = User.objects.create_user(
            username="e31company", email="e31company@example.test",
            password="Password-Of-Tests-123!", role="enterprise", is_active=True,
        )
        Enterprise.objects.create(verified_at=timezone.now(), user=cls.other, company_name="E31 Company", sector="Education")
        for user in (cls.admin, cls.other):
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
        cls.first = Institution.objects.create(
            name="Université du Littoral", acronym="UL", email="contact@ul.example.test",
            is_active=True,
        )
        cls.second = Institution.objects.create(
            name="Académie des Sciences", acronym="AS", is_active=False,
        )
        cls.third = Institution.objects.create(name="École Horizon", is_active=True)
        offer = CommercialOffer.objects.create(
            slug="e31-education", name="Offre campus", kind="flexible",
            audience="institution", quota_unit="accounts", created_by=cls.admin,
        )
        option = PriceOption.objects.create(
            offer=offer, term_months=1, seats=100, amount=30000,
            currency="XOF", created_by=cls.admin,
        )
        today = timezone.localdate()
        cls.subscription = BusinessSubscription.objects.create(
            institution=cls.first, price_option=option, offer_name=offer.name,
            amount=30000, currency="XOF", seats=100, quota_unit="accounts",
            term_months=1, starts_at=today-timedelta(days=1),
            ends_at=today+timedelta(days=20), status="active", created_by=cls.admin,
        )

    def setUp(self):
        self.factory = APIRequestFactory()
        _,self.admin_token = EstablishmentWebSession.issue(self.admin,self.factory.get("/"))
        _,self.other_token = EstablishmentWebSession.issue(self.other,self.factory.get("/"))

    def query(self,params=None,who="admin"):
        headers={}
        if who!="anonymous":
            headers["HTTP_AUTHORIZATION"]="WebToken "+(
                self.admin_token if who=="admin" else self.other_token
            )
        req=self.factory.get("/api/v1/backoffice/institutions/",params or {},**headers)
        return SuperadminInstitutionDirectoryE31.as_view()(req)

    def test_requires_superadmin_verified_browser_session(self):
        self.assertEqual(self.query(who="anonymous").status_code,401)
        self.assertEqual(self.query(who="other").status_code,403)

    def test_real_summary_and_contracts_no_fake_pending_status(self):
        response=self.query()
        self.assertEqual(response.status_code,200)
        data=response.data["data"]
        self.assertEqual(data["summary"]["total"],3)
        self.assertEqual(data["summary"]["active"],2)
        self.assertEqual(data["summary"]["inactive"],1)
        self.assertEqual(data["summary"]["subscribed"],1)
        self.assertEqual(data["summary"]["expiring_30_days"],1)
        self.assertEqual(data["count"],3)
        entries={e["id"]:e for e in data["results"]}
        self.assertEqual(entries[self.first.pk]["subscription"]["capacity"],100)
        self.assertEqual(entries[self.first.pk]["subscription"]["remaining"],100)
        self.assertIsNone(entries[self.second.pk]["subscription"])
        self.assertFalse(entries[self.second.pk]["is_active"])

    def test_search_status_billing_and_pagination(self):
        self.assertEqual(self.query({"search":"littoral"}).data["data"]["count"],1)
        self.assertEqual(self.query({"status":"inactive"}).data["data"]["count"],1)
        self.assertEqual(self.query({"billing":"active"}).data["data"]["count"],1)
        self.assertEqual(self.query({"billing":"none"}).data["data"]["count"],2)
        page=self.query({"page_size":1,"page":2}).data["data"]
        self.assertEqual(page["count"],3)
        self.assertEqual(page["pages"],3)
        self.assertEqual(len(page["results"]),1)

    def test_invalid_filters_never_accepted(self):
        self.assertEqual(self.query({"billing":"invalid"}).status_code,400)
        self.assertEqual(self.query({"page_size":"500"}).status_code,400)
        self.assertEqual(self.query({"page":"garbage"}).status_code,400)
        self.assertEqual(self.query({"page":"100"}).status_code,404)
