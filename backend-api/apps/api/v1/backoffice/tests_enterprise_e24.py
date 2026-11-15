"""Enterprise E24: WebToken-only CRUD with isolation between companies."""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from rest_framework.test import APIRequestFactory

from apps.api.v1.posts.models import Application, Opportunity, Post
from apps.api.v1.subscriptions.models import BusinessSubscription, CommercialOffer, PriceOption
from apps.api.v1.users.models import Enterprise, EstablishmentWebSession, PrivilegedMFADevice, User
from apps.api.v1.backoffice.enterprise_management_e24 import (
    EnterpriseOffersView, EnterpriseOfferDetailView,
    EnterpriseApplicationsView, EnterpriseApplicationDetailView,
    EnterprisePublicationsView,
)


class EnterpriseManagementE24Tests(TestCase):
    def setUp(self):
        self.factory=APIRequestFactory()
        self.users=[]
        self.credentials=[]
        offer=CommercialOffer.objects.get(slug="offre-entreprise-publications")
        tariff=PriceOption.objects.create(
            offer=offer, seats=10, term_months=1, amount=15000, currency="XOF",
        )
        for number in (1,2):
            user=User.objects.create_user(
                username=f"e24_company_{number}",
                email=f"e24_company_{number}@example.test",
                password="Test-E24-Enterprise-Password!",role="enterprise",is_active=True,
            )
            company=Enterprise.objects.create(verified_at=timezone.now(), user=user,company_name=f"Company {number}",sector="Tech")
            BusinessSubscription.objects.create(
                price_option=tariff, enterprise=company, offer_name=offer.name,
                amount=tariff.amount, currency="XOF", seats=10,
                quota_unit="publications", term_months=1,
                starts_at=timezone.localdate(),
                ends_at=timezone.localdate()+timedelta(days=30), status="active",
            )
            PrivilegedMFADevice.objects.create(user=user,
                encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now())
            _,credential=EstablishmentWebSession.issue(user,self.factory.get("/"))
            self.users.append(user)
            self.credentials.append(credential)

    def call(self, view,method,path,data=None,actor=0,**kwargs):
        request=getattr(self.factory,method)(
            path,data=data or {},format="json",
            HTTP_AUTHORIZATION="WebToken "+self.credentials[actor],
        )
        return view.as_view()(request,**kwargs)

    def test_offers_and_applications_isolated(self):
        created=self.call(EnterpriseOffersView,"post","/enterprise/offers/",{
            "title":"Développeur Python","description":"Recrutement junior",
            "category":"job","contract_type":"permanent","location_city":"Dakar",
        })
        self.assertEqual(created.status_code,201,created.data)
        offer_id=created.data["data"]["id"]
        owner=self.call(EnterpriseOffersView,"get","/enterprise/offers/")
        other=self.call(EnterpriseOffersView,"get","/enterprise/offers/",actor=1)
        self.assertEqual(len(owner.data["data"]),1)
        self.assertEqual(other.data["data"],[])
        foreign=self.call(EnterpriseOfferDetailView,"patch","/enterprise/offers/1/",
                          {"status":"closed"},actor=1,offer_id=offer_id)
        self.assertEqual(foreign.status_code,404)

        candidate=User.objects.create_user(username="e24_candidate",email="e24@candidate.test",
            password="Test-E24-Candidate-Password!",role="student",is_active=True)
        application=Application.objects.create(
            user=candidate,opportunity=Opportunity.objects.get(pk=offer_id),
        )
        own=self.call(EnterpriseApplicationsView,"get","/enterprise/applications/")
        others=self.call(EnterpriseApplicationsView,"get","/enterprise/applications/",actor=1)
        self.assertEqual(len(own.data["data"]),1)
        self.assertEqual(others.data["data"],[])
        blocked=self.call(EnterpriseApplicationDetailView,"patch","/enterprise/applications/1/",
                          {"status":"accepted"},actor=1,application_id=application.pk)
        self.assertEqual(blocked.status_code,404)
        changed=self.call(EnterpriseApplicationDetailView,"patch","/enterprise/applications/1/",
                          {"status":"interview"},application_id=application.pk)
        self.assertEqual(changed.status_code,200,changed.data)

    def test_publications_and_webtoken_required(self):
        created=self.call(EnterprisePublicationsView,"post","/enterprise/publications/",{
            "title":"Actualité entreprise","content":"Bienvenue sur notre page.",
        })
        self.assertEqual(created.status_code,201,created.data)
        owner=self.call(EnterprisePublicationsView,"get","/enterprise/publications/")
        other=self.call(EnterprisePublicationsView,"get","/enterprise/publications/",actor=1)
        self.assertEqual(len(owner.data["data"]),1)
        self.assertEqual(other.data["data"],[])
        self.assertEqual(Post.objects.filter(author=self.users[0]).count(),1)
        unverified=EnterpriseOffersView.as_view()(
            self.factory.get("/enterprise/offers/")
        )
        self.assertIn(unverified.status_code,(401,403))

