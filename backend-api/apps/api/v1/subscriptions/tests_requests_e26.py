"""E26 workflow: real MFA-protected requests, organisation isolation, no fictitious payment."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, InstitutionAdmin, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from .models import BusinessSubscription, CommercialOffer, PriceOption, SubscriptionChangeRequest
from .request_views import (
    MySubscriptionRequestsView, SuperadminSubscriptionRequestsView,
    SuperadminSubscriptionRequestDetailView,
)


class SubscriptionRequestsE26Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_user(username="request_admin", email="request-admin@test.dev", password="strong-123-TEST", role="superAdmin", is_active=True)
        self.owner = User.objects.create_user(username="request_owner", email="request-owner@test.dev", password="strong-123-TEST", role="enterprise", is_active=True)
        self.other = User.objects.create_user(username="request_other", email="request-other@test.dev", password="strong-123-TEST", role="enterprise", is_active=True)
        self.school_user = User.objects.create_user(username="request_school", email="request-school@test.dev", password="strong-123-TEST", role="etablissement", is_active=True)
        self.enterprise = Enterprise.objects.create(verified_at=timezone.now(), user=self.owner, company_name="Acme Test", sector="Education")
        self.other_enterprise = Enterprise.objects.create(verified_at=timezone.now(), user=self.other, company_name="Other Test", sector="Education")
        self.school = Institution.objects.create(name="School Test")
        InstitutionAdmin.objects.create(user=self.school_user, institution=self.school)
        self.tokens = {}
        for user in (self.admin, self.owner, self.other, self.school_user):
            PrivilegedMFADevice.objects.create(user=user, encrypted_secret=encrypt_totp(generate_totp_secret()), confirmed_at=timezone.now())
            _, raw = EstablishmentWebSession.issue(user, self.factory.get("/"))
            self.tokens[user.pk] = raw
        self.offer = CommercialOffer.objects.get(slug="offre-entreprise-publications")
        self.price = PriceOption.objects.create(
            offer=self.offer, term_months=6, seats=20, amount="30000.00",
            currency="XOF", created_by=self.admin,
        )
        today = timezone.localdate()
        self.contract = BusinessSubscription.objects.create(
            enterprise=self.enterprise, price_option=self.price, offer_name=self.offer.name,
            amount="30000.00", currency="XOF", seats=20, quota_unit="publications",
            term_months=6, starts_at=today, ends_at=today+timedelta(days=100),
            created_by=self.admin,
        )

    def call(self, view, user, method="get", payload=None, **kwargs):
        authorization="WebToken "+self.tokens[user.pk]
        if method=="get":
            request=self.factory.get("/api/v1/subscriptions/", HTTP_AUTHORIZATION=authorization)
        elif method=="post":
            request=self.factory.post("/api/v1/subscriptions/", payload or {}, format="json", HTTP_AUTHORIZATION=authorization)
        elif method=="patch":
            request=self.factory.patch("/api/v1/subscriptions/", payload or {}, format="json", HTTP_AUTHORIZATION=authorization)
        return view.as_view()(request, **kwargs)

    def test_renewal_request_is_saved_and_only_visible_to_its_organisation(self):
        response=self.call(MySubscriptionRequestsView,self.owner,"post",{
            "request_type":"renewal","requested_term_months":6,"note":"Renouveler",
        })
        self.assertEqual(response.status_code,201)
        saved=SubscriptionChangeRequest.objects.get(pk=response.data["data"]["id"])
        self.assertEqual(saved.enterprise_id,self.enterprise.pk)
        self.assertEqual(saved.source_subscription_id,self.contract.pk)
        self.assertEqual(saved.status,"pending")
        self.assertEqual(len(self.call(MySubscriptionRequestsView,self.other).data["data"]),0)
        self.assertEqual(len(self.call(MySubscriptionRequestsView,self.owner).data["data"]),1)
        self.assertEqual(self.call(MySubscriptionRequestsView,self.owner,"post",{
            "request_type":"renewal","requested_term_months":12,
        }).status_code,409)

    def test_capacity_requires_live_contract_and_rejects_invalid_amount(self):
        bad=self.call(MySubscriptionRequestsView,self.owner,"post",{"request_type":"capacity","requested_quantity":0})
        self.assertEqual(bad.status_code,400)
        no_contract=self.call(MySubscriptionRequestsView,self.other,"post",{"request_type":"capacity","requested_quantity":10})
        self.assertEqual(no_contract.status_code,409)
        good=self.call(MySubscriptionRequestsView,self.owner,"post",{"request_type":"capacity","requested_quantity":10})
        self.assertEqual(good.status_code,201)
        self.assertEqual(good.data["data"]["requested_quantity"],10)

    def test_review_requires_admin_and_does_not_activate_or_charge(self):
        change=self.call(MySubscriptionRequestsView,self.owner,"post",{
            "request_type":"capacity","requested_quantity":10,
        }).data["data"]["id"]
        forbidden=self.call(SuperadminSubscriptionRequestDetailView,self.owner,"patch",{
            "status":"approved",
        },request_id=change)
        self.assertEqual(forbidden.status_code,403)
        admin_list=self.call(SuperadminSubscriptionRequestsView,self.admin).data["data"]
        self.assertEqual(len(admin_list),1)
        approved=self.call(SuperadminSubscriptionRequestDetailView,self.admin,"patch",{
            "status":"approved", "admin_note":"Décision favorable",
        },request_id=change)
        self.assertEqual(approved.status_code,200)
        self.assertTrue(approved.data["data"]["requires_manual_activation"])
        self.assertEqual(self.contract.top_ups.count(),0)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.seats,20)
        self.assertEqual(str(self.contract.amount),"30000.00")
        self.assertEqual(self.call(SuperadminSubscriptionRequestDetailView,self.admin,"patch",{
            "status":"rejected","admin_note":"Non",
        },request_id=change).status_code,409)

    def test_rejection_requires_a_reason_and_scope_filter(self):
        first=self.call(MySubscriptionRequestsView,self.owner,"post",{
            "request_type":"renewal","requested_term_months":1,
        }).data["data"]["id"]
        self.assertEqual(self.call(SuperadminSubscriptionRequestDetailView,self.admin,"patch",{
            "status":"rejected",
        },request_id=first).status_code,400)
        accepted=self.call(SuperadminSubscriptionRequestDetailView,self.admin,"patch",{
            "status":"info_requested","admin_note":"Merci de préciser la durée.",
        },request_id=first)
        self.assertEqual(accepted.status_code,200)
        self.assertEqual(accepted.data["data"]["status"],"info_requested")
        self.assertEqual(len(self.call(SuperadminSubscriptionRequestsView,self.admin).data["data"]),1)
        self.assertEqual(len(self.call(SuperadminSubscriptionRequestsView,self.owner).data.get("data",[])),0)

    def test_institution_can_request_renewal_but_not_other_organisation_data(self):
        response=self.call(MySubscriptionRequestsView,self.school_user,"post",{
            "request_type":"renewal","requested_term_months":12,"note":"Prochaine année",
        })
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data["data"]["organisation_type"],"institution")
        self.assertEqual(len(self.call(MySubscriptionRequestsView,self.owner).data["data"]),0)
