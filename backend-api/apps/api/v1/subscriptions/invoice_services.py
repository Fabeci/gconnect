"""E38 · Invoice issuance business rules (no fabricated receipts/taxes).

Tax and legal issuer data MUST be configured by the Superadmin. The checkout
amount is the gross amount actually verified; it is never recomputed from a
mutable price catalogue. An issued invoice cannot be edited through the API.
"""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    BusinessSubscription, SubscriptionCheckout, InvoiceIssuerProfile,
    InvoiceSequence, IssuedInvoice,
)

ISSUER_FIELDS = (
    "legal_name", "registration_number", "tax_identifier", "address",
    "country_code", "email", "invoice_prefix", "tax_treatment",
    "tax_label", "tax_rate", "exemption_reason",
)
REQUIRED_ISSUER = (
    "legal_name", "registration_number", "tax_identifier",
    "address", "country_code", "email", "invoice_prefix", "tax_treatment",
)
TWO = Decimal("0.01")


class InvoiceConfigurationError(ValueError):
    pass


def _validate_email(address):
    try:
        validate_email(address)
    except ValidationError as exc:
        raise InvoiceConfigurationError("Adresse e-mail de facturation invalide.") from exc


def issuer_dict(issuer):
    if not issuer:
        return {
            "legal_name": "", "registration_number": "", "tax_identifier": "",
            "address": "", "country_code": "", "email": "", "invoice_prefix": "GC",
            "tax_treatment": "", "tax_label": "", "tax_rate": None,
            "exemption_reason": "", "ready": False,
        }
    data = {key: getattr(issuer, key) for key in ISSUER_FIELDS}
    data["tax_rate"] = str(issuer.tax_rate) if issuer.tax_rate is not None else None
    try:
        require_valid_issuer(data)
        data["ready"] = True
    except InvoiceConfigurationError:
        data["ready"] = False
    return data


def require_valid_issuer(data):
    missing = [name for name in REQUIRED_ISSUER if not str(data.get(name) or "").strip()]
    if missing:
        raise InvoiceConfigurationError(
            "Informations légales de l'émetteur manquantes : " + ", ".join(missing)
        )
    if not re.fullmatch(r"[A-Z]{2}", str(data.get("country_code", ""))):
        raise InvoiceConfigurationError("Pays : code ISO à 2 lettres requis.")
    if not re.fullmatch(r"[A-Z][A-Z0-9]{0,9}", str(data.get("invoice_prefix", ""))):
        raise InvoiceConfigurationError("Préfixe : 1 à 10 lettres majuscules ou chiffres.")
    _validate_email(data["email"])
    treatment = data.get("tax_treatment")
    if treatment not in ("included", "exempt"):
        raise InvoiceConfigurationError("Choisissez le régime fiscal réel.")
    if treatment == "included":
        if not str(data.get("tax_label") or "").strip():
            raise InvoiceConfigurationError("Libellé de la taxe obligatoire.")
        try:
            rate = Decimal(str(data["tax_rate"]))
        except (KeyError, TypeError, InvalidOperation) as exc:
            raise InvoiceConfigurationError("Taux de taxe explicite obligatoire.") from exc
        if not rate.is_finite() or rate <= 0 or rate > 100 or rate.as_tuple().exponent < -2:
            raise InvoiceConfigurationError("Taux de taxe invalide (0 < taux <= 100).")
    else:
        if not str(data.get("exemption_reason") or "").strip():
            raise InvoiceConfigurationError("Indiquez la base légale de l'exonération.")
        rate = Decimal("0")
    return rate


def normalise_issuer_payload(payload):
    if not isinstance(payload, dict):
        raise InvoiceConfigurationError("Configuration juridique invalide.")
    limits = {
        "legal_name": 200, "registration_number": 90, "tax_identifier": 90,
        "address": 2000, "country_code": 2, "email": 254,
        "invoice_prefix": 10, "tax_treatment": 20, "tax_label": 50,
        "exemption_reason": 250,
    }
    data = {}
    for name, length in limits.items():
        value = str(payload.get(name) or "").strip()
        if len(value) > length:
            raise InvoiceConfigurationError("Champ trop long : " + name)
        data[name] = value
    data["country_code"] = data["country_code"].upper()
    data["invoice_prefix"] = data["invoice_prefix"].upper()
    rate = payload.get("tax_rate")
    data["tax_rate"] = None if rate is None or str(rate).strip() == "" else str(rate).strip()
    decimal_rate = require_valid_issuer(data)
    data["tax_rate"] = decimal_rate
    return data


def normalise_buyer(payload, order):
    if not isinstance(payload, dict):
        raise InvoiceConfigurationError("Informations client manquantes.")
    if order.enterprise_id:
        buyer_name = order.enterprise.company_name.strip()
        fallback_email = order.enterprise.user.email
        kind = "enterprise"
    else:
        buyer_name = order.institution.name.strip()
        fallback_email = order.institution.email
        kind = "institution"
    address = str(payload.get("buyer_address") or "").strip()
    country = str(payload.get("buyer_country_code") or "").strip().upper()
    contact = str(payload.get("buyer_email") or fallback_email or "").strip()
    tax_number = str(payload.get("buyer_tax_identifier") or "").strip()
    if not buyer_name or not address or not country or not contact:
        raise InvoiceConfigurationError("Client : nom, adresse, pays et e-mail obligatoires.")
    if len(buyer_name) > 255 or len(address) > 2000 or len(tax_number) > 90:
        raise InvoiceConfigurationError("Informations client trop longues.")
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise InvoiceConfigurationError("Pays client : code ISO à 2 lettres requis.")
    _validate_email(contact)
    return {
        "legal_name": buyer_name, "address": address,
        "country_code": country, "email": contact,
        "tax_identifier": tax_number, "organisation_type": kind,
        "organisation_id": order.enterprise_id or order.institution_id,
    }


def _match_checkout(order):
    if (order.status != SubscriptionCheckout.Status.PAID
        or order.verified_at is None or order.activated_subscription_id is None):
        raise InvoiceConfigurationError("Aucune facture sans paiement prestataire vérifié et contrat lié.")
    contract = order.activated_subscription
    if (
        contract.enterprise_id != order.enterprise_id or
        contract.institution_id != order.institution_id or
        contract.amount != order.amount or
        contract.currency != order.currency or
        contract.seats != order.capacity or
        contract.quota_unit != order.quota_unit or
        contract.term_months != order.term_months
    ):
        raise InvoiceConfigurationError("Incohérence du paiement et du contrat, émission bloquée.")
    return contract


def _issue_once(checkout_id, buyer_data, user):
    with transaction.atomic():
        order = SubscriptionCheckout.objects.select_for_update().select_related(
            "enterprise__user", "institution", "activated_subscription",
        ).get(pk=checkout_id)
        existing = IssuedInvoice.objects.filter(checkout_id=order.id).first()
        if existing is not None:
            return existing, False
        contract = _match_checkout(order)
        issuer = InvoiceIssuerProfile.objects.select_for_update().filter(pk=1).first()
        settings_snapshot = issuer_dict(issuer)
        require_valid_issuer(settings_snapshot)
        buyer = normalise_buyer(buyer_data, order)
        now = timezone.now()
        seq, _ = InvoiceSequence.objects.select_for_update().get_or_create(year=now.year)
        seq.last_number += 1
        seq.save(update_fields=["last_number"])
        number = f"{issuer.invoice_prefix}-{now.year}-{seq.last_number:06d}"
        gross = Decimal(order.amount).quantize(TWO)
        rate = Decimal(str(settings_snapshot["tax_rate"]))
        if issuer.tax_treatment == "included":
            net = (gross / (Decimal("1") + rate / Decimal("100"))).quantize(
                TWO, rounding=ROUND_HALF_UP,
            )
            tax = gross - net
        else:
            net, tax = gross, Decimal("0.00")
        sale = {
            "offer_name": order.offer_name, "capacity": order.capacity,
            "quota_unit": order.quota_unit, "term_months": order.term_months,
            "starts_at": contract.starts_at.isoformat(),
            "ends_at": contract.ends_at.isoformat(),
            "transaction_id": str(order.transaction_id),
            "verified_at": order.verified_at.isoformat(),
            "payment_provider": order.provider,
        }
        invoice = IssuedInvoice.objects.create(
            checkout=order, subscription=contract, year=now.year,
            sequence_number=seq.last_number, number=number,
            issuer_snapshot=settings_snapshot, customer_snapshot=buyer,
            sale_snapshot=sale, amount_net=net, amount_tax=tax,
            amount_total=gross, currency=order.currency,
            issued_at=now, issued_by=user,
        )
        return invoice, True


def issue_invoice(checkout_id, buyer_data, user):
    """Idempotent issuance. Unique checkout + yearly sequence are DB-constrained."""
    for attempt in range(3):
        try:
            return _issue_once(checkout_id, buyer_data, user)
        except IntegrityError:
            existing = IssuedInvoice.objects.filter(checkout_id=checkout_id).first()
            if existing is not None:
                return existing, False
            if attempt == 2:
                raise
    raise InvoiceConfigurationError("La numérotation de facture a échoué.")


def serialise_invoice(invoice):
    return {
        "id": invoice.id, "number": invoice.number,
        "checkout_id": invoice.checkout_id,
        "organisation_type": invoice.customer_snapshot.get("organisation_type"),
        "organisation_name": invoice.customer_snapshot.get("legal_name"),
        "buyer_email": invoice.customer_snapshot.get("email"),
        "offer_name": invoice.sale_snapshot.get("offer_name"),
        "transaction_id": invoice.sale_snapshot.get("transaction_id"),
        "subscription_id": invoice.subscription_id,
        "amount_net": str(invoice.amount_net),
        "amount_tax": str(invoice.amount_tax),
        "amount_total": str(invoice.amount_total),
        "currency": invoice.currency,
        "issued_at": invoice.issued_at.isoformat(),
        "tax_treatment": invoice.issuer_snapshot.get("tax_treatment"),
        "tax_label": invoice.issuer_snapshot.get("tax_label"),
        "tax_rate": invoice.issuer_snapshot.get("tax_rate"),
    }
