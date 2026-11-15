"""E38 · MFA-protected invoice configuration, issue, history and PDF access."""
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication
from .models import InvoiceIssuerProfile, IssuedInvoice, SubscriptionCheckout
from .invoice_services import (
    InvoiceConfigurationError, normalise_issuer_payload, issuer_dict,
    issue_invoice, serialise_invoice,
)
from .invoice_pdf import render_invoice_pdf
from .views import _organisation_for


def _no_store(response):
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _paginate(request, query):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    paginator = Paginator(query, 20)
    selected = paginator.get_page(page)
    return {
        "results": [serialise_invoice(invoice) for invoice in selected],
        "page": selected.number, "pages": paginator.num_pages,
        "count": paginator.count,
    }


def _pdf_response(invoice):
    data = render_invoice_pdf(invoice)
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{invoice.number}.pdf"'
    response["Content-Length"] = str(len(data))
    return _no_store(response)


class _Admin(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]


class InvoiceIssuerSettingsE38(_Admin):
    def get(self, request):
        return _no_store(success_response(
            "Identité légale de facturation.", issuer_dict(
                InvoiceIssuerProfile.objects.filter(pk=1).first(),
            ),
        ))

    def put(self, request):
        try:
            values = normalise_issuer_payload(request.data)
        except InvoiceConfigurationError as exc:
            return error_response(str(exc), status_code=400)
        with transaction.atomic():
            issuer, _ = InvoiceIssuerProfile.objects.select_for_update().get_or_create(pk=1)
            if (issuer.invoice_prefix != values["invoice_prefix"]
                    and IssuedInvoice.objects.exists()):
                return error_response(
                    "Impossible de changer le préfixe après émission : préserver la séquence.",
                    status_code=409,
                )
            for name, value in values.items():
                setattr(issuer, name, value)
            issuer.save()
        log_audit_event("invoice_issuer_settings_updated", user=request.user, request=request, metadata={
            "issuer_id": 1, "tax_treatment": issuer.tax_treatment,
        })
        return _no_store(success_response("Informations légales enregistrées.", issuer_dict(issuer)))


class InvoiceListE38(_Admin):
    def get(self, request):
        query = IssuedInvoice.objects.select_related("checkout", "subscription")
        search = request.query_params.get("search", "").strip()[:100]
        if search:
            query = query.filter(
                Q(number__icontains=search)
                | Q(checkout__enterprise__company_name__icontains=search)
                | Q(checkout__institution__name__icontains=search)
            )
        items = _paginate(request,query.order_by("-issued_at", "-pk"))
        items["issued_total"] = IssuedInvoice.objects.count()
        items["total_invoiced_xof"] = str(
            IssuedInvoice.objects.filter(currency="XOF").aggregate(total=Sum("amount_total"))["total"]
            or 0
        )
        return _no_store(success_response("Historique des factures émises.", items))


class InvoiceIssueE38(_Admin):
    def post(self, request):
        try:
            checkout_id = int(request.data.get("checkout_id"))
            if checkout_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return error_response("Identifiant de paiement invalide.", status_code=400)
        try:
            invoice, created = issue_invoice(checkout_id, request.data, request.user)
        except SubscriptionCheckout.DoesNotExist:
            return error_response("Paiement introuvable.", status_code=404)
        except InvoiceConfigurationError as exc:
            return error_response(str(exc), status_code=400)
        except IntegrityError:
            return error_response("Conflit de numérotation, réessayez.", status_code=409)
        if created:
            log_audit_event("invoice_issued", user=request.user, request=request, metadata={
                "invoice_id": invoice.pk,
                "number": invoice.number, "checkout_id": checkout_id,
            })
        return _no_store(success_response(
            "Facture créée." if created else "Facture existante (sans doublon).",
            {"invoice": serialise_invoice(invoice), "created": created},
            status_code=201 if created else 200,
        ))


class InvoiceAdminPdfE38(_Admin):
    def get(self, request, invoice_id):
        invoice = IssuedInvoice.objects.filter(pk=invoice_id).first()
        if invoice is None:
            return error_response("Facture introuvable.", status_code=404)
        log_audit_event("invoice_pdf_downloaded", user=request.user, request=request, metadata={
            "invoice_id": invoice.pk,
        })
        return _pdf_response(invoice)


class _ProfessionalInvoices(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def scoped(self, request):
        role, org = _organisation_for(request.user)
        if role == "enterprise" and org is not None:
            return IssuedInvoice.objects.filter(checkout__enterprise=org)
        if role == "institution" and org is not None:
            return IssuedInvoice.objects.filter(checkout__institution=org)
        return IssuedInvoice.objects.none()


class MyInvoicesE38(_ProfessionalInvoices):
    def get(self, request):
        if request.user.role not in ("enterprise", "etablissement"):
            return error_response("Accès réservé aux organisations.", status_code=403)
        items = _paginate(request, self.scoped(request).order_by("-issued_at","-pk"))
        return _no_store(success_response("Vos factures émises.", items))


class MyInvoicePdfE38(_ProfessionalInvoices):
    def get(self, request, invoice_id):
        if request.user.role not in ("enterprise", "etablissement"):
            return error_response("Accès réservé aux organisations.", status_code=403)
        invoice = self.scoped(request).filter(pk=invoice_id).first()
        if invoice is None:
            # Do not reveal whether another tenant has the requested invoice.
            return error_response("Facture introuvable.", status_code=404)
        return _pdf_response(invoice)
