"""E38 regression: legal gate, real payment, immutable invoice, PDF, tenant isolation."""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.utils import timezone
from pypdf import PdfReader
from rest_framework.test import APIRequestFactory

from apps.api.v1.subscriptions.models import (
    InvoiceIssuerProfile, IssuedInvoice, BusinessSubscription,
    CommercialOffer, PriceOption, SubscriptionCheckout,
)
from apps.api.v1.subscriptions.invoice_views import (
    InvoiceIssuerSettingsE38, InvoiceIssueE38, InvoiceListE38,
    InvoiceAdminPdfE38, MyInvoicesE38, MyInvoicePdfE38,
)
from apps.api.v1.users.models import (
    User, Enterprise, EnterpriseMember, EstablishmentWebSession, PrivilegedMFADevice,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class IssuedInvoiceE38Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = self.person("superAdmin", "admininvoice")
        self.customer_user = self.person("enterprise", "buyerinvoice")
        self.enterprise = Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.customer_user, company_name="Client G-Connect Test", sector="IT",
        )
        self.other_user = self.person("enterprise", "otherinvoice")
        self.other_enterprise = Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.other_user, company_name="Autre Entreprise", sector="IT",
        )
        self.tokens = {}
        for key, user in (("admin",self.admin),("buyer",self.customer_user),("other",self.other_user)):
            _, token = EstablishmentWebSession.issue(user,self.factory.get("/"))
            self.tokens[key] = token
        self.offer = CommercialOffer.objects.create(
            slug="e38-test", name="Publication validée", kind="flexible",
            quota_unit="publications", audience="enterprise", created_by=self.admin,
        )
        self.price = PriceOption.objects.create(
            offer=self.offer, term_months=1, seats=20,
            amount=Decimal("15000.00"), currency="XOF", created_by=self.admin,
        )
        self.checkout = self.order(self.enterprise, verified=True)

    def person(self, role, name):
        user=User.objects.create_user(
            username=name,email=name+"@example.test",
            password="Secure-Test-Pass-2026!",role=role,is_active=True,
        )
        PrivilegedMFADevice.objects.create(
            user=user,encrypted_secret=encrypt_totp(generate_totp_secret()),
            confirmed_at=timezone.now(),
        )
        return user

    def order(self, enterprise, verified):
        contract=None
        if verified:
            contract=BusinessSubscription.objects.create(
                enterprise=enterprise, price_option=self.price,
                offer_name="Publication validée", amount=Decimal("15000.00"),
                currency="XOF", seats=20, quota_unit="publications",term_months=1,
                starts_at=timezone.localdate(),
                ends_at=timezone.localdate()+timedelta(days=31),
                status="active",created_by=self.admin,
            )
        return SubscriptionCheckout.objects.create(
            enterprise=enterprise,price_option=self.price,
            activated_subscription=contract,offer_name="Publication validée",
            capacity=20,quota_unit="publications",term_months=1,
            amount=Decimal("15000.00"),currency="XOF",created_by=enterprise.user,
            status="paid" if verified else "pending",
            verified_at=timezone.now() if verified else None,
        )

    def request(self, view, route, method="get", data=None, user="admin", **kwargs):
        headers={} if user is None else {"HTTP_AUTHORIZATION":"WebToken "+self.tokens[user]}
        request=getattr(self.factory,method)(route, data=data, format="json",**headers)
        return view.as_view()(request,**kwargs)

    def configure(self, treatment="included", rate="18.00"):
        data={
            "legal_name":"G-Connect Exemple Tests (ne pas utiliser en production)",
            "registration_number":"RCCM-TEST-001",
            "tax_identifier":"NINEA-TEST-002",
            "address":"Adresse juridique de test, Dakar",
            "country_code":"SN","email":"factures@example.test","invoice_prefix":"GCT",
            "tax_treatment":treatment,
            "tax_label":"TVA" if treatment=="included" else "",
            "tax_rate":rate if treatment=="included" else "0",
            "exemption_reason":"Justificatif fiscal de test" if treatment=="exempt" else "",
        }
        result=self.request(InvoiceIssuerSettingsE38,"/backoffice/finance/issuer/",method="put",data=data)
        self.assertEqual(result.status_code,200,result.data)
        self.assertTrue(result.data["data"]["ready"])

    def issue(self, checkout=None, user="admin", buyer=None):
        data={
            "checkout_id": (checkout or self.checkout).id,
            "buyer_address":"Adresse du client, Dakar",
            "buyer_country_code":"SN",
            "buyer_email":"facturation-client@example.test",
            "buyer_tax_identifier":"ID-FISCAL-CLIENT-TEST",
        }
        if buyer is not None:
            data.update(buyer)
        return self.request(InvoiceIssueE38, "/backoffice/finance/invoices/issue/",
                            method="post",data=data,user=user)

    def test_unconfigured_issuer_cannot_issue_or_guess_tax(self):
        self.assertEqual(self.issue().status_code,400)
        self.assertEqual(IssuedInvoice.objects.count(),0)
        invalid=self.request(InvoiceIssuerSettingsE38,"/backoffice/finance/issuer/",
            method="put",data={"legal_name":"Just a name"})
        self.assertEqual(invalid.status_code,400)
        self.assertEqual(InvoiceIssuerProfile.objects.count(),0)

    def test_no_invoice_for_pending_checkout_or_fake_paid_flag(self):
        self.configure()
        pending=self.order(self.other_enterprise, verified=False)
        self.assertEqual(self.issue(pending).status_code,400)
        pending.status="paid"
        pending.save(update_fields=["status"])
        self.assertEqual(self.issue(pending).status_code,400)
        self.assertEqual(IssuedInvoice.objects.count(),0)

    def test_issuer_configuration_and_role_are_protected(self):
        self.assertEqual(self.request(InvoiceListE38,"/finance/invoices/",user="buyer").status_code,403)
        self.assertEqual(self.request(InvoiceIssuerSettingsE38,"/finance/issuer/",user=None).status_code,401)
        self.assertEqual(self.issue(user="buyer").status_code,403)
        self.assertEqual(self.request(InvoiceIssueE38,"/finance/invoices/issue/",method="get").status_code,405)
        self.configure()
        current=self.request(InvoiceIssuerSettingsE38,"/finance/issuer/")
        self.assertEqual(current.data["data"]["invoice_prefix"],"GCT")

    def test_real_issue_idempotency_unchanged_snapshots_and_year_sequence(self):
        self.configure()
        first=self.issue()
        self.assertEqual(first.status_code,201,first.data)
        number=first.data["data"]["invoice"]["number"]
        self.assertRegex(number,r"^GCT-\d{4}-000001$")
        same=self.issue(buyer={"buyer_address":"Adresse différente"})
        self.assertEqual(same.status_code,200)
        self.assertEqual(first.data["data"]["invoice"]["number"],same.data["data"]["invoice"]["number"])
        self.assertEqual(IssuedInvoice.objects.count(),1)
        snap=IssuedInvoice.objects.get()
        self.assertEqual(snap.customer_snapshot["address"],"Adresse du client, Dakar")
        self.assertEqual(snap.amount_total,Decimal("15000.00"))
        self.assertEqual(snap.amount_net,Decimal("12711.86"))
        self.assertEqual(snap.amount_tax,Decimal("2288.14"))
        # Change the product tariff: already-issued documents remain unchanged.
        self.price.amount=Decimal("99000.00")
        self.price.save(update_fields=["amount"])
        self.assertEqual(IssuedInvoice.objects.get().amount_total,Decimal("15000.00"))
        other=self.order(self.other_enterprise,verified=True)
        again=self.issue(other)
        self.assertEqual(again.status_code,201)
        self.assertRegex(again.data["data"]["invoice"]["number"],r"-000002$")
        self.assertEqual(len(set(IssuedInvoice.objects.values_list("number",flat=True))),2)

    def test_pdf_real_binary_text_and_strict_tenant_isolation(self):
        self.configure(treatment="exempt")
        first=self.issue()
        invoice_id=first.data["data"]["invoice"]["id"]
        own=self.request(MyInvoicePdfE38,"/subscriptions/invoices/1/pdf/",user="buyer",invoice_id=invoice_id)
        self.assertEqual(own.status_code,200)
        self.assertEqual(own["Content-Type"],"application/pdf")
        self.assertEqual(own["Cache-Control"],"no-store")
        self.assertTrue(own.content.startswith(b"%PDF"))
        pdf=PdfReader(BytesIO(own.content))
        self.assertGreaterEqual(len(pdf.pages),1)
        text=pdf.pages[0].extract_text()
        self.assertIn(first.data["data"]["invoice"]["number"],text)
        self.assertIn("Client G-Connect Test",text)
        self.assertIn("15000.00 XOF",text)
        self.assertEqual(
            self.request(MyInvoicePdfE38,"/subscriptions/invoices/1/pdf/",
                user="other",invoice_id=invoice_id).status_code,404)
        self.assertEqual(
            self.request(MyInvoicesE38,"/subscriptions/invoices/my/",user="other").data["data"]["count"],0)
        self.assertEqual(
            self.request(MyInvoicesE38,"/subscriptions/invoices/my/",user="buyer").data["data"]["count"],1)
        self.assertEqual(
            self.request(InvoiceAdminPdfE38,"/finance/invoices/1/pdf/",invoice_id=invoice_id).status_code,200)
        self.assertEqual(IssuedInvoice.objects.get().amount_tax,Decimal("0.00"))

    def test_issuer_prefix_locks_after_first_invoice(self):
        self.configure()
        self.assertEqual(self.issue().status_code,201)
        update={
            "legal_name":"New legal issuer", "registration_number":"RCCM-002",
            "tax_identifier":"TAX-002","address":"Dakar, Sénégal",
            "country_code":"SN","email":"new@example.test",
            "invoice_prefix":"ALT","tax_treatment":"included",
            "tax_label":"TVA","tax_rate":"18.00",
        }
        self.assertEqual(
            self.request(InvoiceIssuerSettingsE38,"/finance/issuer/",method="put",data=update).status_code,
            409,
        )
        self.assertEqual(IssuedInvoice.objects.count(),1)

    def test_e53_recruiter_cannot_read_owner_invoices_or_issue_new_ones(self):
        recruiter = self.person("enterprise", "invoice_recruiter_e53")
        EnterpriseMember.objects.create(user=recruiter, enterprise=self.enterprise)
        _, self.tokens["recruiter"] = EstablishmentWebSession.issue(recruiter, self.factory.get("/"))
        self.configure()
        issued = self.issue()
        invoice_id = issued.data["data"]["invoice"]["id"]
        listed = self.request(MyInvoicesE38, "/subscriptions/invoices/my/", user="recruiter")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["data"]["count"], 0)
        self.assertEqual(self.request(
            MyInvoicePdfE38, "/subscriptions/invoices/1/pdf/",
            user="recruiter", invoice_id=invoice_id,
        ).status_code, 404)
        self.assertEqual(self.issue(user="recruiter").status_code, 403)
