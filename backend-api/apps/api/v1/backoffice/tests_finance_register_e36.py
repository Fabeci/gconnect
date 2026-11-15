"""E36 · Finance register is read-only and grounded in verified transactions."""
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.api.v1.backoffice.finance_register_e36 import SuperadminFinanceRegisterE36
from apps.api.v1.subscriptions.models import (
    CommercialOffer, PriceOption, BusinessSubscription, SubscriptionCheckout,
)
from apps.api.v1.users.models import (
    Enterprise, User, EstablishmentWebSession, PrivilegedMFADevice,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class FinanceRegisterE36Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_user(
            username="finance_admin", email="finance-admin@example.test",
            password="Secure-Test-Pass-2026!", role="superAdmin", is_active=True,
        )
        self.company_user = User.objects.create_user(
            username="finance_company", email="finance-org@example.test",
            password="Secure-Test-Pass-2026!", role="enterprise", is_active=True,
        )
        self.company = Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.company_user, company_name="Acme Finance E36", sector="IT",
        )
        for person in (self.admin, self.company_user):
            PrivilegedMFADevice.objects.create(
                user=person, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
        _, self.token = EstablishmentWebSession.issue(self.admin, self.factory.get("/"))
        _, self.company_token = EstablishmentWebSession.issue(
            self.company_user, self.factory.get("/"),
        )
        self.offer = CommercialOffer.objects.create(
            slug="finance-e36", name="Publications", kind="flexible",
            quota_unit="publications", audience="enterprise", created_by=self.admin,
        )
        self.price = PriceOption.objects.create(
            offer=self.offer, term_months=1, seats=20,
            amount=Decimal("15000.00"), currency="XOF", created_by=self.admin,
        )

    def query(self, query="", token="admin", method="get"):
        tokens = {"admin":self.token, "company":self.company_token}
        kwargs = {} if token == "anonymous" else {
            "HTTP_AUTHORIZATION": "WebToken " + tokens[token],
        }
        factory_method = getattr(self.factory, method)
        request = factory_method("/api/v1/backoffice/finance/register/?" + query, **kwargs)
        return SuperadminFinanceRegisterE36.as_view()(request)

    def checkout(self, status, amount="15000.00", verified=False):
        contract = None
        if verified:
            contract = BusinessSubscription.objects.create(
                enterprise=self.company, price_option=self.price,
                offer_name="Publications", amount=Decimal(amount), currency="XOF",
                seats=20, quota_unit="publications", term_months=1,
                starts_at=timezone.localdate(),
                ends_at=timezone.localdate()+timedelta(days=31),
                status="active", created_by=self.admin,
            )
        return SubscriptionCheckout.objects.create(
            enterprise=self.company, price_option=self.price,
            activated_subscription=contract,
            offer_name="Publications", amount=Decimal(amount), currency="XOF",
            capacity=20, quota_unit="publications", term_months=1,
            status=status, verified_at=timezone.now() if verified else None,
            created_by=self.company_user,
        )

    def test_requires_web_mfa_superadmin(self):
        self.assertEqual(self.query(token="anonymous").status_code, 401)
        self.assertEqual(self.query(token="company").status_code, 403)
        self.assertEqual(self.query(method="post").status_code, 405)

    def test_empty_register_does_not_invent_invoices_or_revenue(self):
        response = self.query()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        data = response.data["data"]
        self.assertEqual(data["results"], [])
        self.assertEqual(data["summary"]["verified_total_xof"], "0.00")
        self.assertFalse(data["summary"]["invoicing_available"])

    def test_only_provider_verified_paid_orders_count_as_receipts(self):
        self.checkout("paid", verified=True)
        self.checkout("paid")  # Defensive: corrupted paid flag is NOT proof.
        self.checkout("pending", amount="45000")
        self.checkout("failed", amount="65000")
        response = self.query()
        data = response.data["data"]
        self.assertEqual(data["summary"]["paid"], 1)
        self.assertEqual(data["summary"]["unverified_paid"], 1)
        self.assertEqual(data["summary"]["pending"], 1)
        self.assertEqual(data["summary"]["failed"], 1)
        self.assertEqual(Decimal(data["summary"]["verified_total_xof"]), Decimal("15000"))
        paid = self.query("status=paid").data["data"]
        self.assertEqual(paid["count"], 1)
        self.assertTrue(paid["results"][0]["is_verified"])
        self.assertEqual(paid["results"][0]["organisation_name"], "Acme Finance E36")
        self.assertNotIn("checkout_url", paid["results"][0])
        self.assertIsNone(paid["results"][0]["invoice_number"])
        unverified = [x for x in data["results"] if x["status"] == "paid" and not x["is_verified"]]
        self.assertEqual(len(unverified), 1)
        self.assertIsNone(unverified[0]["verified_at"])

    def test_filters_are_safe_and_do_not_expand_scope(self):
        checkout = self.checkout("pending")
        self.checkout("failed")
        result = self.query("status=pending&search=Acme")
        self.assertEqual(result.data["data"]["count"], 1)
        selected = self.query("status=pending&search=" + str(checkout.transaction_id))
        self.assertEqual(selected.data["data"]["count"], 1)
        self.assertEqual(self.query("status=invalid&page=abc").status_code, 200)
        self.assertEqual(self.query("status=failed&search=not-found").data["data"]["count"], 0)
