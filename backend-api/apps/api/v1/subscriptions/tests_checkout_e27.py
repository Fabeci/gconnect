"""E27: only verified provider payments may grant an organisation quota."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, InstitutionAdmin, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from .checkout_views import CheckoutStartView, CheckoutVerifyView, CheckoutOrdersView, CheckoutNotificationView
from .models import BusinessSubscription, CommercialOffer, PriceOption, SubscriptionCheckout
from .quotas import current_contract


class CheckoutE27Tests(TestCase):
    def setUp(self):
        self.factory=APIRequestFactory()
        self.admin=User.objects.create_user(
            username="checkout_admin",email="checkout-admin@example.test",password="a-strong-pass",role="superAdmin",is_active=True,
        )
        self.company_user=User.objects.create_user(
            username="checkout_company",email="checkout-company@example.test",password="a-strong-pass",role="enterprise",is_active=True,
        )
        self.school_user=User.objects.create_user(
            username="checkout_school",email="checkout-school@example.test",password="a-strong-pass",role="etablissement",is_active=True,
        )
        self.company=Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.company_user,company_name="Company E27",sector="IT",
        )
        self.school=Institution.objects.create(name="School E27")
        InstitutionAdmin.objects.create(user=self.school_user,institution=self.school)
        self.tokens={}
        for user in (self.admin,self.company_user,self.school_user):
            PrivilegedMFADevice.objects.create(
                user=user,encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
            _,token=EstablishmentWebSession.issue(user,self.factory.get("/"))
            self.tokens[user.pk]=token
        self.offer=CommercialOffer.objects.get(slug="offre-entreprise-publications")
        self.price=PriceOption.objects.create(
            offer=self.offer,term_months=6,seats=20,amount=Decimal("30000"),
            currency="XOF",created_by=self.admin,
        )
        self.school_offer=CommercialOffer.objects.get(slug="offre-flexible")
        self.school_price=PriceOption.objects.create(
            offer=self.school_offer,term_months=1,seats=100,
            amount=Decimal("30000"),currency="XOF",created_by=self.admin,
        )
        self.config={
            "enabled":True, "provider":"cinetpay",
            "web_origin":"https://gconnect.example.test",
        }

    def call(self, view,user,method="post",body=None,**kwargs):
        auth="WebToken "+self.tokens[user.pk]
        if method=="post":
            req=self.factory.post("/",body or {},format="json",HTTP_AUTHORIZATION=auth)
        else:
            req=self.factory.get("/",HTTP_AUTHORIZATION=auth)
        return view.as_view()(req,**kwargs)

    def checkout(self,user=None,price=None):
        with patch("apps.api.v1.subscriptions.checkout_views.configuration",return_value=self.config), patch(
            "apps.api.v1.subscriptions.checkout_views.create_checkout",
            return_value="https://checkout.cinetpay.com/payment/approved123",
        ):
            return self.call(CheckoutStartView,user or self.company_user,body={
                "price_option_id":(price or self.price).pk,
            })

    def test_checkout_creates_pending_order_but_never_grants_quota(self):
        result=self.checkout()
        self.assertEqual(result.status_code,201)
        self.assertEqual(BusinessSubscription.objects.count(),0)
        order=SubscriptionCheckout.objects.get()
        self.assertEqual(order.amount,Decimal("30000"))
        self.assertEqual(order.quota_unit,"publications")
        self.assertEqual(result.data["data"]["status"],"pending")
        self.assertEqual(result.data["data"]["checkout_url"],"https://checkout.cinetpay.com/payment/approved123")
        self.assertEqual(self.call(CheckoutStartView,self.company_user,body={"price_option_id":self.price.id}).status_code,503)
        self.assertEqual(self.checkout().status_code,409)

    def test_only_correct_organisation_can_pay_its_catalog(self):
        wrong=self.checkout(self.school_user,self.price)
        self.assertEqual(wrong.status_code,409)
        own=self.checkout(self.school_user,self.school_price)
        self.assertEqual(own.status_code,201)
        self.assertEqual(SubscriptionCheckout.objects.get().quota_unit,"accounts")
        self.assertEqual(
            len(self.call(CheckoutOrdersView,self.company_user,method="get").data["data"]),0,
        )

    def test_verified_success_grants_once_and_does_not_trust_client_state(self):
        started=self.checkout()
        txn=started.data["data"]["transaction_id"]
        with patch("apps.api.v1.subscriptions.checkout_views.verify_checkout",return_value="accepted"), patch(
            "apps.api.v1.subscriptions.checkout_views.configuration",return_value=self.config,
        ):
            first=self.call(CheckoutVerifyView,self.company_user,body={},transaction_id=txn)
            again=self.call(CheckoutVerifyView,self.company_user,body={},transaction_id=txn)
        self.assertEqual(first.status_code,200)
        self.assertEqual(again.status_code,200)
        self.assertEqual(BusinessSubscription.objects.filter(enterprise=self.company).count(),1)
        self.assertEqual(first.data["data"]["status"],"paid")
        self.assertIn("/entreprise?forfait=",first.data["data"]["access_url"])
        self.assertTrue(first.data["data"]["access_url"].endswith("#subscription"))
        self.assertEqual(first.data["data"]["activation_status"],"actif")

    def test_renewal_scheduled_after_current_end_without_losing_days(self):
        old=BusinessSubscription.objects.create(
            enterprise=self.company,price_option=self.price,offer_name=self.offer.name,
            amount=Decimal("30000"),currency="XOF",seats=20,quota_unit="publications",
            term_months=6,starts_at=timezone.localdate(),
            ends_at=timezone.localdate()+timedelta(days=35),created_by=self.admin,
        )
        started=self.checkout()
        with patch("apps.api.v1.subscriptions.checkout_views.verify_checkout",return_value="accepted"), patch(
            "apps.api.v1.subscriptions.checkout_views.configuration",return_value=self.config,
        ):
            verified=self.call(CheckoutVerifyView,self.company_user,transaction_id=started.data["data"]["transaction_id"])
        self.assertEqual(verified.status_code,200)
        next_contract=BusinessSubscription.objects.exclude(pk=old.pk).get()
        self.assertEqual(next_contract.status,"scheduled")
        self.assertEqual(next_contract.starts_at,old.ends_at)
        self.assertEqual(next_contract.amount,Decimal("30000"))
        self.assertEqual(verified.data["data"]["activation_status"],"programmé")
        with patch("apps.api.v1.subscriptions.quotas.timezone.localdate",return_value=old.ends_at):
            current=current_contract(enterprise=self.company)
        self.assertEqual(current.pk,next_contract.pk)
        old.refresh_from_db()
        self.assertEqual(old.status,"active")

    def test_provider_rejection_never_grants_plan(self):
        started=self.checkout()
        with patch("apps.api.v1.subscriptions.checkout_views.verify_checkout",return_value="refused"):
            result=self.call(CheckoutVerifyView,self.company_user,transaction_id=started.data["data"]["transaction_id"])
        self.assertEqual(result.data["data"]["status"],"failed")
        self.assertEqual(BusinessSubscription.objects.count(),0)

    def test_webhook_ignores_forged_identifier_without_verifying_remote(self):
        request=self.factory.post("/",{"cpm_trans_id":"not-a-transaction"},format="json")
        result=CheckoutNotificationView.as_view()(request)
        self.assertEqual(result.status_code,200)
        self.assertEqual(BusinessSubscription.objects.count(),0)

    def test_other_organisation_cannot_verify_payment(self):
        started=self.checkout()
        other=self.call(CheckoutVerifyView,self.school_user,transaction_id=started.data["data"]["transaction_id"])
        self.assertEqual(other.status_code,404)

    def test_amount_currency_verified_by_provider_not_browser(self):
        from .cinetpay import CheckoutProviderError, verify_checkout
        started=self.checkout()
        order=SubscriptionCheckout.objects.get(transaction_id=started.data["data"]["transaction_id"])
        with patch("apps.api.v1.subscriptions.cinetpay.configuration",return_value={
                "enabled":True,"api_key":"fake","site_id":"fake",
            }), patch("apps.api.v1.subscriptions.cinetpay._response",return_value={
                "code":"00","data":{"status":"ACCEPTED","amount":"1","currency":"XOF"},
            }):
            with self.assertRaises(CheckoutProviderError):
                verify_checkout(order)
        self.assertEqual(BusinessSubscription.objects.count(),0)


    def test_expired_previous_active_row_does_not_block_verified_new_purchase(self):
        past=timezone.localdate()-timedelta(days=1)
        old=BusinessSubscription.objects.create(
            enterprise=self.company,price_option=self.price,offer_name=self.offer.name,
            amount=Decimal("30000"),currency="XOF",seats=20,quota_unit="publications",
            term_months=6,starts_at=past-timedelta(days=60),ends_at=past,
            status="active",created_by=self.admin,
        )
        started=self.checkout()
        with patch("apps.api.v1.subscriptions.checkout_views.verify_checkout",return_value="accepted"), patch(
            "apps.api.v1.subscriptions.checkout_views.configuration",return_value=self.config,
        ):
            verified=self.call(CheckoutVerifyView,self.company_user,transaction_id=started.data["data"]["transaction_id"])
        self.assertEqual(verified.status_code,200)
        old.refresh_from_db()
        self.assertEqual(old.status,"ended")
        self.assertEqual(BusinessSubscription.objects.filter(enterprise=self.company,status="active").count(),1)
