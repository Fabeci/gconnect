"""E22 price-matrix tests: role isolation, time-based catalog and immutable snapshots."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.subscriptions.models import BusinessSubscription, CommercialOffer, PriceOption
from apps.api.v1.subscriptions.views import (
    CatalogView, MySubscriptionView, SuperadminOffersView, SuperadminPricesView,
    SuperadminAssignmentsView, SuperadminAssignmentDetailView, SuperadminPriceDetailView,
)
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, InstitutionAdmin, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class SubscriptionPricingE22Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_user(
            username="e22_admin", email="e22-admin@example.test", password="E22-Pass-Strong!",
            role="superAdmin", is_active=True,
        )
        self.user_a = User.objects.create_user(
            username="e22_company_a", email="e22-company-a@example.test",
            password="E22-Pass-Strong!", role="enterprise", is_active=True,
        )
        self.user_b = User.objects.create_user(
            username="e22_company_b", email="e22-company-b@example.test",
            password="E22-Pass-Strong!", role="enterprise", is_active=True,
        )
        self.company_a = Enterprise.objects.create(verified_at=timezone.now(), user=self.user_a, company_name="Entreprise A", sector="Services")
        self.company_b = Enterprise.objects.create(verified_at=timezone.now(), user=self.user_b, company_name="Entreprise B", sector="Industrie")
        self.school = Institution.objects.create(name="École E22")
        self.school_admin = User.objects.create_user(
            username="e22_school", email="e22-school@example.test",
            password="E22-Pass-Strong!", role="etablissement", is_active=True,
        )
        InstitutionAdmin.objects.create(user=self.school_admin, institution=self.school)
        self.tokens = {}
        for user in (self.admin, self.user_a, self.user_b, self.school_admin):
            # A WebToken is usable only after confirmed MFA. Tests must satisfy
            # the real authentication invariant, not bypass it.
            PrivilegedMFADevice.objects.create(
                user=user,
                encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
            _, raw = EstablishmentWebSession.issue(user, self.factory.get("/"))
            self.tokens[user.pk] = raw

    def call(self, view, user, method="get", payload=None, path="/api/v1/subscriptions/"):
        if method == "get":
            request = self.factory.get(path, HTTP_AUTHORIZATION="WebToken " + self.tokens[user.pk])
        elif method == "post":
            request = self.factory.post(path, payload or {}, format="json",
                                        HTTP_AUTHORIZATION="WebToken " + self.tokens[user.pk])
        elif method == "patch":
            request = self.factory.patch(path, payload or {}, format="json",
                                         HTTP_AUTHORIZATION="WebToken " + self.tokens[user.pk])
        return view.as_view()(request)

    def make_price(self, offer, term=6, seats=200, amount="240000.00"):
        return self.call(SuperadminPricesView, self.admin, "post", {
            "offer_id": offer.pk, "term_months": term, "seats": seats,
            "amount": amount, "currency": "XOF",
        })

    def test_default_families_and_role_scoped_catalog(self):
        self.assertEqual(CommercialOffer.objects.count(), 3)
        flexible = CommercialOffer.objects.get(slug="offre-flexible")
        self.assertEqual(flexible.kind, "flexible")
        self.assertEqual(CommercialOffer.objects.get(slug="offre-par-compte").kind, "per_account")
        enterprise_offer = CommercialOffer.objects.get(slug="offre-entreprise-publications")
        self.assertEqual(enterprise_offer.quota_unit, "publications")
        self.assertEqual(enterprise_offer.audience, "enterprise")
        institution_offer = CommercialOffer.objects.create(
            slug="schools-only", name="Pour écoles", kind="flexible",
            audience="institution",
        )
        self.make_price(institution_offer)
        company = self.call(CatalogView, self.user_a).data["data"]
        school = self.call(CatalogView, self.school_admin).data["data"]
        self.assertNotIn("schools-only", [o["slug"] for o in company])
        self.assertIn("schools-only", [o["slug"] for o in school])
        self.assertIn("offre-entreprise-publications", [o["slug"] for o in company])
        self.assertNotIn("offre-entreprise-publications", [o["slug"] for o in school])
        self.assertEqual(CommercialOffer.objects.get(pk=flexible.pk).price_options.count(), 0)

    def test_enterprise_offer_cannot_use_per_account_model(self):
        rejected = self.call(SuperadminOffersView, self.admin, "post", {
            "slug": "entreprise-par-compte", "name": "Offre Entreprise erronée",
            "kind": "per_account", "audience": "enterprise",
            "quota_unit": "publications",
        })
        self.assertEqual(rejected.status_code, 400)
        self.assertFalse(CommercialOffer.objects.filter(slug="entreprise-par-compte").exists())

    def test_price_matrix_four_terms_two_seat_packs_and_version_history(self):
        offer = CommercialOffer.objects.get(slug="offre-par-compte")
        for months in (1, 6, 12, 0):
            payload = self.make_price(offer, term=months, seats=200,
                                      amount=None if months == 0 else "18000.00")
            self.assertEqual(payload.status_code, 201)
        second = self.make_price(offer, term=6, seats=500, amount="350000.00")
        self.assertEqual(second.status_code, 201)
        old = PriceOption.objects.get(offer=offer, term_months=6, seats=200)
        replacement = self.make_price(offer, term=6, seats=200, amount="19000.00")
        self.assertEqual(replacement.status_code, 201)
        old.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertEqual(PriceOption.objects.filter(offer=offer, is_active=True).count(), 5)
        self.assertEqual(PriceOption.objects.filter(offer=offer).count(), 6)
        self.assertEqual(self.call(SuperadminPricesView, self.user_a, "post", {
            "offer_id": offer.pk, "term_months": 12, "seats": 200, "amount": "1",
        }).status_code, 403)

    def test_assignments_are_private_and_snapshot_survives_repricing(self):
        offer = CommercialOffer.objects.get(slug="offre-entreprise-publications")
        price = self.make_price(offer, term=12, seats=200, amount="120000.00")
        price_id = price.data["data"]["id"]
        assigned = self.call(SuperadminAssignmentsView, self.admin, "post", {
            "price_option_id": price_id, "enterprise_id": self.company_a.pk,
        })
        self.assertEqual(assigned.status_code, 201)
        self.assertEqual(assigned.data["data"]["amount"], "120000.00")
        self.assertEqual(self.call(SuperadminAssignmentsView, self.admin, "post", {
            "price_option_id": price_id, "enterprise_id": self.company_a.pk,
        }).status_code, 409)
        self.assertEqual(self.call(MySubscriptionView, self.user_a).data["data"]["current"]["amount"], "120000.00")
        self.assertIsNone(self.call(MySubscriptionView, self.user_b).data["data"]["current"])
        self.assertEqual(self.make_price(offer, term=12, seats=200, amount="175000.00").status_code, 201)
        recorded = self.call(MySubscriptionView, self.user_a).data["data"]["current"]
        self.assertEqual(recorded["amount"], "120000.00")
        self.assertEqual(recorded["seats"], 200)
        self.assertEqual(recorded["quota_unit"], "publications")
        self.assertEqual(BusinessSubscription.objects.count(), 1)

    def test_organisation_assignment_rejects_wrong_audience(self):
        offer = CommercialOffer.objects.create(
            slug="only-company", name="Entreprises uniquement",
            kind="per_account", audience="enterprise",
        )
        price = self.make_price(offer, term=1, seats=50, amount="4500.00")
        self.assertEqual(self.call(SuperadminAssignmentsView, self.admin, "post", {
            "price_option_id": price.data["data"]["id"],
            "institution_id": self.school.pk,
        }).status_code, 403)
        flex = CommercialOffer.objects.get(slug="offre-flexible")
        school_price = self.make_price(flex, term=1, seats=50, amount="7000.00")
        result = self.call(SuperadminAssignmentsView, self.admin, "post", {
            "price_option_id": school_price.data["data"]["id"], "institution_id": self.school.pk,
        })
        self.assertEqual(result.status_code, 201)
        school_subscription = self.call(MySubscriptionView, self.school_admin).data["data"]
        self.assertEqual(school_subscription["current"]["institution_id"], self.school.pk)
        self.assertIsNone(school_subscription["current"]["enterprise_id"])
        self.assertEqual(self.call(MySubscriptionView, self.user_a).data["data"]["history"], [])

    def test_quote_requires_explicit_negotiated_amount_and_end_date(self):
        offer = CommercialOffer.objects.get(slug="offre-entreprise-publications")
        quote = self.make_price(offer, term=0, seats=500, amount=None)
        self.assertEqual(quote.status_code, 201)
        price_id = quote.data["data"]["id"]
        missing = self.call(SuperadminAssignmentsView, self.admin, "post", {
            "price_option_id": price_id, "enterprise_id": self.company_b.pk,
        })
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(BusinessSubscription.objects.count(), 0)
        future = (timezone.localdate() + timedelta(days=180)).isoformat()
        assigned = self.call(SuperadminAssignmentsView, self.admin, "post", {
            "price_option_id": price_id, "enterprise_id": self.company_b.pk,
            "quoted_amount": "750000.00", "ends_at": future,
        })
        self.assertEqual(assigned.status_code, 201)
        self.assertEqual(assigned.data["data"]["amount"], "750000.00")
        suspend_request = self.factory.patch(
            "/api/v1/subscriptions/admin/assignments/1/",
            {"status": "suspended"}, format="json",
            HTTP_AUTHORIZATION="WebToken " + self.tokens[self.admin.pk],
        )
        self.assertEqual(SuperadminAssignmentDetailView.as_view()(
            suspend_request, subscription_id=assigned.data["data"]["id"],
        ).status_code, 200)

    def test_current_subscription_is_found_beyond_last_thirty_history_rows(self):
        offer = CommercialOffer.objects.get(slug="offre-entreprise-publications")
        price = self.make_price(offer, term=12, seats=200, amount="120000.00")
        option = PriceOption.objects.get(pk=price.data["data"]["id"])
        today = timezone.localdate()
        active = BusinessSubscription.objects.create(
            price_option=option, enterprise=self.company_a,
            offer_name=offer.name, amount=option.amount, currency=option.currency,
            seats=option.seats, quota_unit="publications", term_months=option.term_months,
            starts_at=today, ends_at=today + timedelta(days=365),
            status="active", created_by=self.admin,
        )
        for day in range(31):
            BusinessSubscription.objects.create(
                price_option=option, enterprise=self.company_a,
                offer_name=offer.name, amount=option.amount, currency=option.currency,
                seats=option.seats, quota_unit="publications", term_months=option.term_months,
                starts_at=today - timedelta(days=day + 2),
                ends_at=today - timedelta(days=day + 1),
                status="ended", created_by=self.admin,
            )
        response = self.call(MySubscriptionView, self.user_a)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["current"]["id"], active.pk)
        self.assertEqual(len(response.data["data"]["history"]), 30)

    def test_superadmin_can_retire_a_price_without_deleting_history(self):
        offer = CommercialOffer.objects.get(slug="offre-par-compte")
        price = self.make_price(offer, term=6, seats=200, amount="15000.00")
        pid = price.data["data"]["id"]
        req = self.factory.patch(
            "/api/v1/subscriptions/admin/prices/"+str(pid)+"/",
            {"is_active": False}, format="json",
            HTTP_AUTHORIZATION="WebToken " + self.tokens[self.admin.pk],
        )
        removed = SuperadminPriceDetailView.as_view()(req, price_id=pid)
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(PriceOption.objects.get(pk=pid).is_active)
        self.assertEqual(PriceOption.objects.filter(offer=offer).count(), 1)
        school_catalog = self.call(CatalogView, self.school_admin).data["data"]
        self.assertEqual(next(o for o in school_catalog if o["slug"] == "offre-par-compte")["prices"], [])

    def test_invalid_pricing_does_not_remove_existing_rate_and_mobile_token_is_rejected(self):
        offer = CommercialOffer.objects.get(slug="offre-flexible")
        self.make_price(offer, term=6, seats=200, amount="12000.00")
        bad = self.make_price(offer, term=6, seats=200, amount="-999")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(PriceOption.objects.filter(offer=offer, term_months=6, seats=200, is_active=True).count(), 1)
        mobile_token = Token.objects.create(user=self.user_a)
        request = self.factory.get("/api/v1/subscriptions/my/",
                                   HTTP_AUTHORIZATION="Token " + mobile_token.key)
        self.assertIn(MySubscriptionView.as_view()(request).status_code, (401, 403))
        self.assertEqual(self.call(SuperadminOffersView, self.user_a).status_code, 403)

