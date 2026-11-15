"""E32: business portfolio is truthful, protected and publication-based."""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.api.v1.backoffice.enterprise_directory_e32 import SuperadminEnterpriseDirectoryE32
from apps.api.v1.users.models import User, Enterprise, PrivilegedMFADevice, EstablishmentWebSession
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from apps.api.v1.subscriptions.models import (
    CommercialOffer, PriceOption, BusinessSubscription, PublicationConsumption, SubscriptionTopUp
)
from apps.api.v1.posts.models import Post, Opportunity, Application


class EnterpriseDirectoryE32Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="e32admin", email="e32admin@example.test",
            password="Long-Password-E32!", role="superAdmin", is_active=True)
        cls.viewer = User.objects.create_user(username="e32other", email="e32other@example.test",
            password="Long-Password-E32!", role="enterprise", is_active=True)
        cls.applicant = User.objects.create_user(username="e32applicant", email="e32student@example.test",
            password="Long-Password-E32!", role="student", is_active=True)
        for u in (cls.admin, cls.viewer):
            PrivilegedMFADevice.objects.create(
                user=u, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
        cls.first = Enterprise.objects.create(verified_at=timezone.now(), user=cls.viewer,
            company_name="Acme Technologies", sector="Informatique", website="https://example.com")
        cls.other_user = User.objects.create_user(username="e32inactive", email="e32inactive@example.test",
            password="Long-Password-E32!", role="enterprise", is_active=False)
        cls.second = Enterprise.objects.create(verified_at=timezone.now(), user=cls.other_user,
            company_name="Étoile Conseil", sector="Conseil")
        offer = CommercialOffer.objects.create(slug="e32-pub", name="Publications",
            kind="flexible", audience="enterprise", quota_unit="publications", created_by=cls.admin)
        price = PriceOption.objects.create(offer=offer, term_months=1, seats=20, amount=5000,
            currency="XOF", created_by=cls.admin)
        today = timezone.localdate()
        cls.subscription = BusinessSubscription.objects.create(
            enterprise=cls.first, price_option=price, offer_name=offer.name,
            amount=5000, currency="XOF", seats=20, quota_unit="publications",
            term_months=1, starts_at=today-timedelta(days=1),
            ends_at=today+timedelta(days=15), status="active", created_by=cls.admin)
        SubscriptionTopUp.objects.create(
            subscription=cls.subscription, quantity=5, amount=1000, currency="XOF",
            created_by=cls.admin)
        cls.post = Post.objects.create(author=cls.viewer, title="Poste Développeur",
            content="Offre de stage", post_type=Post.PostType.OPPORTUNITY)
        cls.opportunity = Opportunity.objects.create(
            post=cls.post, enterprise=cls.first, status=Opportunity.Status.OPEN)
        Application.objects.create(user=cls.applicant, opportunity=cls.opportunity)
        PublicationConsumption.objects.create(
            subscription=cls.subscription, post=cls.post, title_snapshot=cls.post.title)
        # An intentionally deleted post still consumes credit.
        PublicationConsumption.objects.create(
            subscription=cls.subscription, post=None, title_snapshot="Offre supprimée")

    def setUp(self):
        factory=APIRequestFactory()
        self.factory=factory
        _, self.admin_token = EstablishmentWebSession.issue(self.admin, factory.get("/"))
        _, self.viewer_token = EstablishmentWebSession.issue(self.viewer, factory.get("/"))

    def query(self, params=None, who="admin"):
        headers={}
        if who!="anonymous":
            token=self.admin_token if who=="admin" else self.viewer_token
            headers["HTTP_AUTHORIZATION"]="WebToken "+token
        return SuperadminEnterpriseDirectoryE32.as_view()(
            self.factory.get("/api/v1/backoffice/enterprises/",params or {},**headers)
        )

    def test_protected_superadmin_only(self):
        self.assertEqual(self.query(who="anonymous").status_code,401)
        self.assertEqual(self.query(who="viewer").status_code,403)

    def test_portfolio_is_real_and_deleted_post_does_not_refund_credit(self):
        response=self.query()
        self.assertEqual(response.status_code,200)
        data=response.data["data"]
        self.assertEqual(data["count"],2)
        self.assertEqual(data["summary"]["total"],2)
        self.assertEqual(data["summary"]["active"],1)
        self.assertEqual(data["summary"]["subscribed"],1)
        self.assertEqual(data["summary"]["expiring_30_days"],1)
        rows={x["id"]:x for x in data["results"]}
        first=rows[self.first.pk]
        self.assertEqual(first["open_offers"],1)
        self.assertEqual(first["offers_count"],1)
        self.assertEqual(first["applications_count"],1)
        self.assertEqual(first["subscription"]["capacity"],25)
        self.assertEqual(first["subscription"]["used"],2)
        self.assertEqual(first["subscription"]["remaining"],23)
        self.assertEqual(first["subscription"]["unit"],"publications")
        self.assertIsNone(rows[self.second.pk]["subscription"])
        self.assertFalse(rows[self.second.pk]["is_active"])

    def test_search_status_billing_and_pagination(self):
        self.assertEqual(self.query({"search":"Informatique"}).data["data"]["count"],1)
        self.assertEqual(self.query({"status":"active"}).data["data"]["count"],1)
        self.assertEqual(self.query({"status":"inactive"}).data["data"]["count"],1)
        self.assertEqual(self.query({"billing":"active"}).data["data"]["count"],1)
        self.assertEqual(self.query({"billing":"none"}).data["data"]["count"],1)
        page=self.query({"page":2,"page_size":1}).data["data"]
        self.assertEqual(page["count"],2)
        self.assertEqual(page["pages"],2)
        self.assertEqual(len(page["results"]),1)

    def test_invalid_filters_and_page_protected(self):
        self.assertEqual(self.query({"status":"unknown"}).status_code,400)
        self.assertEqual(self.query({"page_size":100}).status_code,400)
        self.assertEqual(self.query({"page":"invalid"}).status_code,400)
        self.assertEqual(self.query({"page":99}).status_code,404)
