"""E25: consumption ledger, real enterprise writes and concurrent school seats."""
from datetime import timedelta

from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.api.v1.backoffice.enterprise_management_e24 import (
    EnterpriseOffersView, EnterprisePublicationsView,
)
from apps.api.v1.establishments.models import Institution, StudentInstitution
from apps.api.v1.posts.models import Post
from apps.api.v1.subscriptions.models import (
    BusinessSubscription, CommercialOffer, PriceOption, PublicationConsumption,
)
from apps.api.v1.subscriptions.quotas import (
    QuotaExceeded, active_institution_accounts, consume_enterprise_publication,
    lock_institution, require_available_school_seat,
)
from apps.api.v1.subscriptions.views import InstitutionSeatsView, SuperadminTopUpView
from apps.api.v1.users.models import Enterprise, InstitutionAdmin, Student, User


class OrganisationQuotaTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = User.objects.create_user(
            username="quota_enterprise", email="quota-enterprise@example.test",
            password="Test-Quota-Password!", role="enterprise", is_active=True,
        )
        self.enterprise = Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.owner, company_name="Entreprise Test", sector="Services",
        )
        self.admin = User.objects.create_user(
            username="quota_admin", email="quota-admin@example.test",
            password="Test-Quota-Password!", role="superAdmin", is_active=True,
        )
        self.school = Institution.objects.create(name="École Quota E25")
        self.school_user = User.objects.create_user(
            username="quota_school", email="quota-school@example.test",
            password="Test-Quota-Password!", role="etablissement", is_active=True,
        )
        InstitutionAdmin.objects.create(user=self.school_user, institution=self.school)

    def contract(self, *, enterprise=False, quantity=2, starts=None, ends=None):
        unit = "publications" if enterprise else "accounts"
        offer = CommercialOffer.objects.get(
            slug="offre-entreprise-publications" if enterprise else "offre-flexible",
        )
        price = PriceOption.objects.create(
            offer=offer, seats=quantity, term_months=1, amount=10000, currency="XOF",
        )
        today = timezone.localdate()
        return BusinessSubscription.objects.create(
            price_option=price, enterprise=self.enterprise if enterprise else None,
            institution=None if enterprise else self.school,
            offer_name=offer.name, amount=price.amount, currency="XOF", seats=quantity,
            quota_unit=unit, term_months=1, starts_at=starts or today,
            ends_at=ends or today + timedelta(days=30), status="active",
        )

    def request(self, view, user, method="post", data=None, **kwargs):
        req = getattr(self.factory, method)("/api/v1/", data or {}, format="json")
        force_authenticate(req, user=user)
        return view.as_view()(req, **kwargs)

    def test_enterprise_limit_survives_deletion_and_can_be_extended(self):
        contract = self.contract(enterprise=True, quantity=2)
        for index in (1, 2):
            response = self.request(EnterpriseOffersView, self.owner, data={
                "title": f"Offre test {index}", "description": "Description professionnelle",
                "category": "job", "contract_type": "permanent", "location_city": "Dakar",
            })
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(contract.publication_consumptions.count(), 2)
        self.assertEqual(self.request(EnterpriseOffersView, self.owner, data={
            "title": "Troisième offre", "description": "Description professionnelle",
            "category": "job", "contract_type": "permanent", "location_city": "Dakar",
        }).status_code, 409)
        first_id = contract.publication_consumptions.first().post_id
        Post.objects.get(pk=first_id).delete()
        self.assertEqual(contract.publication_consumptions.count(), 2)
        self.assertEqual(self.request(EnterpriseOffersView, self.owner, data={
            "title": "Après suppression", "description": "Description professionnelle",
            "category": "job", "contract_type": "permanent", "location_city": "Dakar",
        }).status_code, 409)
        extra = self.request(SuperadminTopUpView, self.admin, data={
            "quantity": 1, "amount": "2500.00", "note": "Crédit supplémentaire",
        }, subscription_id=contract.pk)
        self.assertEqual(extra.status_code, 201)
        self.assertEqual(extra.data["data"]["quota"]["limit"], 3)
        added = self.request(EnterprisePublicationsView, self.owner, data={
            "title": "Publication autorisée", "content": "Contenu professionnel",
        })
        self.assertEqual(added.status_code, 201)
        self.assertEqual(contract.publication_consumptions.count(), 3)
        self.assertEqual(self.request(EnterprisePublicationsView, self.owner, data={
            "title": "Publication refusée", "content": "Contenu professionnel",
        }).status_code, 409)

    def test_drafts_do_not_consume_and_republishing_same_post_costs_once(self):
        contract = self.contract(enterprise=True, quantity=1)
        post = Post.objects.create(
            author=self.owner, title="Brouillon", content="En préparation", is_draft=True,
        )
        consume_enterprise_publication(self.enterprise, post)
        self.assertEqual(PublicationConsumption.objects.count(), 0)
        post.is_draft = False
        post.save(update_fields=["is_draft"])
        consume_enterprise_publication(self.enterprise, post)
        post.is_archived = True
        post.save(update_fields=["is_archived"])
        consume_enterprise_publication(self.enterprise, post)
        self.assertEqual(contract.publication_consumptions.count(), 1)

    def test_expired_contract_and_foreign_enterprise_cannot_publish(self):
        self.contract(enterprise=True, quantity=1,
                      starts=timezone.localdate() - timedelta(days=60),
                      ends=timezone.localdate() - timedelta(days=1))
        response = self.request(EnterpriseOffersView, self.owner, data={
            "title": "Offre hors contrat", "description": "Description",
            "category": "job", "contract_type": "permanent", "location_city": "Dakar",
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Post.objects.filter(author=self.owner).count(), 0)
        self.assertEqual(self.request(SuperadminTopUpView, self.owner, data={
            "quantity": 1, "amount": "100",
        }, subscription_id=BusinessSubscription.objects.first().pk).status_code, 403)

    def test_school_seats_count_activated_members_not_feed_preferences(self):
        self.contract(quantity=1)
        student_user = User.objects.create_user(
            username="school_student", email="student@example.test",
            password="Test-Quota-Password!", role="student", is_active=True,
        )
        student = Student.objects.create(
            user=student_user, gender="M", date_of_birth="2000-01-01", student_id="QUOTA-123",
        )
        link = StudentInstitution.objects.create(student=student, institution=self.school, is_active=False)
        self.assertEqual(active_institution_accounts(self.school), 1)
        with transaction.atomic():
            lock_institution(self.school.pk)
            with self.assertRaises(QuotaExceeded):
                require_available_school_seat(self.school)
        disable = self.request(InstitutionSeatsView, self.school_user, method="patch", data={
            "role": "student", "id": link.pk, "seat_enabled": False,
        })
        self.assertEqual(disable.status_code, 200)
        self.assertEqual(active_institution_accounts(self.school), 0)
        enable = self.request(InstitutionSeatsView, self.school_user, method="patch", data={
            "role": "student", "id": link.pk, "seat_enabled": True,
        })
        self.assertEqual(enable.status_code, 200)
        self.assertEqual(active_institution_accounts(self.school), 1)

    def test_school_cannot_modify_foreign_membership(self):
        self.contract(quantity=1)
        other = Institution.objects.create(name="Autre école")
        user = User.objects.create_user(
            username="outside_student", email="outside@example.test",
            password="Test-Quota-Password!", role="student", is_active=True,
        )
        student = Student.objects.create(
            user=user, gender="F", date_of_birth="2001-01-01", student_id="QUOTA-999",
        )
        foreign = StudentInstitution.objects.create(student=student, institution=other)
        response = self.request(InstitutionSeatsView, self.school_user, method="patch", data={
            "role": "student", "id": foreign.pk, "seat_enabled": False,
        })
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertTrue(foreign.seat_enabled)
