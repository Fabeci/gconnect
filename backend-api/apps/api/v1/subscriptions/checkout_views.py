"""Professional self-service hosted checkout, verified payment, and safe plan access.

A payment URL is not an access credential. A verified purchase unlocks the existing
organisation-scoped session; login and MFA remain required on both portals.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import Enterprise
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication

from .cinetpay import (
    CheckoutConfigurationError, CheckoutProviderError,
    configuration, create_checkout, public_configuration, verify_checkout,
)
from .models import (
    BusinessSubscription, CommercialOffer, PriceOption, SubscriptionCheckout,
)
from .quotas import current_contract
from .views import _organisation_for, _plus_months


def _criteria(user):
    role, org = _organisation_for(user)
    if role not in ("enterprise", "institution") or org is None:
        return None, None, None
    return role, org, ({"enterprise": org} if role == "enterprise" else {"institution": org})


def _access_url(order):
    if order.status != SubscriptionCheckout.Status.PAID or not order.activated_subscription_id:
        return None
    origin = configuration()["web_origin"]
    if not origin:
        return None
    return (origin + ("/entreprise" if order.enterprise_id else "/etablissement")
            + "?forfait=" + str(order.activated_subscription_id) + "#subscription")


def _email_access_confirmation(order):
    """Best-effort receipt, never an authentication link or a payment assertion by itself."""
    address = (getattr(order.created_by, "email", None) or "").strip()
    link = _access_url(order)
    if not address or not link:
        return
    subscription = order.activated_subscription
    if not subscription:
        return
    try:
        send_mail(
            subject="G-Connect : votre forfait est confirmé",
            message=(
                "Votre paiement a été vérifié par notre prestataire.\n\n"
                f"Forfait : {order.offer_name}\n"
                f"Capacité : {order.capacity} {order.quota_unit}\n"
                f"Début : {subscription.starts_at}\n"
                f"Échéance : {subscription.ends_at}\n\n"
                f"Accéder à votre espace : {link}\n\n"
                "Votre compte et la double authentification restent obligatoires.\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[address],
            fail_silently=True,
        )
    except Exception:
        # E-mail failures must not roll back a confirmed, already-paid contract.
        pass


def _serialize(order):
    subscription = order.activated_subscription
    return {
        "transaction_id": str(order.transaction_id), "status": order.status,
        "provider": order.provider,
        "offer_name": order.offer_name, "capacity": order.capacity,
        "quota_unit": order.quota_unit, "term_months": order.term_months,
        "amount": str(order.amount), "currency": order.currency,
        "created_at": order.created_at.isoformat(),
        "checkout_url": order.checkout_url if order.status == "pending" else None,
        "access_url": _access_url(order),
        "subscription_id": subscription.pk if subscription else None,
        "starts_at": subscription.starts_at.isoformat() if subscription else None,
        "ends_at": subscription.ends_at.isoformat() if subscription else None,
        "activation_status": (
            "programmé" if subscription and subscription.starts_at > timezone.localdate()
            else "actif" if subscription else "en attente"
        ),
    }


def _orders():
    return SubscriptionCheckout.objects.select_related(
        "activated_subscription", "price_option", "institution", "enterprise",
    )


class _ProfessionalOnly(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


class CheckoutConfigurationView(_ProfessionalOnly):
    def get(self, request):
        role, org, criteria = _criteria(request.user)
        if not criteria:
            return error_response("Organisation professionnelle requise.", status_code=403)
        return success_response("Configuration du paiement en ligne.", public_configuration())


class CheckoutOrdersView(_ProfessionalOnly):
    def get(self, request):
        role, org, criteria = _criteria(request.user)
        if not criteria:
            return error_response("Organisation professionnelle requise.", status_code=403)
        items = _orders().filter(**criteria)[:25]
        return success_response("Historique de vos paiements et commandes.", [_serialize(o) for o in items])


class CheckoutStartView(_ProfessionalOnly):
    def post(self, request):
        role, org, criteria = _criteria(request.user)
        if not criteria:
            return error_response("Organisation professionnelle requise.", status_code=403)
        config = configuration()
        if not config["enabled"]:
            return error_response("Paiement en ligne non activé. Envoyez une demande au Superadmin.", status_code=503)
        raw_id = request.data.get("price_option_id")
        if type(raw_id) not in (int, str) or not str(raw_id).isdigit() or int(raw_id) < 1:
            return error_response("Sélectionnez un tarif disponible.")
        with transaction.atomic():
            # Lock the owner rather than the order to serialize competing checkouts.
            if role == "enterprise":
                Enterprise.objects.select_for_update().get(pk=org.pk)
            else:
                Institution.objects.select_for_update().get(pk=org.pk)
            try:
                price = PriceOption.objects.select_related("offer").get(pk=int(raw_id))
            except PriceOption.DoesNotExist:
                return error_response("Tarif introuvable.", status_code=404)
            expected_unit = "publications" if role == "enterprise" else "accounts"
            if (not price.is_active or not price.offer.is_active
                    or price.offer.audience not in ("all", role)
                    or price.offer.quota_unit != expected_unit
                    or price.term_months not in (1, 6, 12)
                    or price.amount is None or price.amount <= 0 or price.currency != "XOF"
                    or price.amount != price.amount.to_integral_value() or int(price.amount) % 5):
                return error_response("Ce forfait ne peut pas être payé directement. Utilisez une demande.", status_code=409)
            if BusinessSubscription.objects.filter(
                **criteria, status="scheduled", starts_at__gt=timezone.localdate(),
                ends_at__gt=timezone.localdate(),
            ).exists():
                return error_response("Un renouvellement est déjà programmé pour cette organisation.", status_code=409)
            pending = _orders().filter(**criteria, status="pending").first()
            if pending is not None:
                return error_response(
                    "Un paiement est déjà en attente. Vérifiez son état avant de recommencer.",
                    status_code=409,
                )
            active = current_contract(
                enterprise=org if role == "enterprise" else None,
                institution=org if role == "institution" else None, lock=True,
            )
            order = SubscriptionCheckout.objects.create(
                **criteria, price_option=price, source_subscription=active,
                offer_name=price.offer.name, capacity=price.seats,
                quota_unit=price.offer.quota_unit, term_months=price.term_months,
                amount=price.amount, currency=price.currency, created_by=request.user,
            )
        try:
            link = create_checkout(order)
        except (CheckoutConfigurationError, CheckoutProviderError) as exc:
            SubscriptionCheckout.objects.filter(pk=order.pk, status="pending").update(status="failed")
            return error_response(str(exc), status_code=502)
        SubscriptionCheckout.objects.filter(pk=order.pk, status="pending").update(checkout_url=link)
        order.checkout_url = link
        log_audit_event("subscription_checkout_started", user=request.user, request=request, metadata={
            "checkout_id": order.pk, "price_option_id": price.pk, "organisation_type": role,
        })
        return success_response("Paiement préparé auprès de CinetPay.", _serialize(order), status_code=201)


def _sync_verified(order_id, *, request=None, user=None):
    """Only a verified CinetPay ACCEPTED result can activate the exact quoted plan."""
    try:
        fresh = _orders().get(pk=order_id)
    except SubscriptionCheckout.DoesNotExist:
        return None
    if fresh.status == "paid":
        return fresh
    if fresh.status != "pending":
        return fresh
    verified = verify_checkout(fresh)
    if verified == "pending":
        return fresh
    if verified == "refused":
        SubscriptionCheckout.objects.filter(pk=fresh.pk, status="pending").update(status="failed")
        return _orders().get(pk=fresh.pk)
    with transaction.atomic():
        order = _orders().select_for_update().get(pk=order_id)
        if order.status != "pending":
            return order
        criteria = {"enterprise": order.enterprise} if order.enterprise_id else {"institution": order.institution}
        if order.enterprise_id:
            Enterprise.objects.select_for_update().get(pk=order.enterprise_id)
        else:
            Institution.objects.select_for_update().get(pk=order.institution_id)
        today = timezone.localdate()
        already = BusinessSubscription.objects.filter(
            **criteria, status="scheduled", starts_at__gt=today, ends_at__gt=today,
        ).exists()
        if already:
            # Do not silently discard a confirmed payment or create a double contract.
            raise CheckoutProviderError("Paiement vérifié, mais un renouvellement est déjà programmé : examen manuel requis.")
        active = current_contract(
            enterprise=order.enterprise if order.enterprise_id else None,
            institution=order.institution if order.institution_id else None, lock=True,
        )
        # Expired rows must release the active uniqueness constraint.
        BusinessSubscription.objects.filter(
            **criteria, status="active", ends_at__lte=today,
        ).update(status="ended")
        begins = max(today, active.ends_at) if active is not None else today
        ends = _plus_months(begins, order.term_months)
        contract = BusinessSubscription(
            **criteria, price_option=order.price_option, offer_name=order.offer_name,
            amount=order.amount, currency=order.currency, seats=order.capacity,
            quota_unit=order.quota_unit, term_months=order.term_months,
            starts_at=begins, ends_at=ends,
            status="scheduled" if begins > today else "active",
            created_by=order.created_by,
        )
        contract.full_clean()
        contract.save()
        order.activated_subscription = contract
        order.status = "paid"
        order.verified_at = timezone.now()
        order.save(update_fields=["activated_subscription", "status", "verified_at"])
        transaction.on_commit(lambda: _email_access_confirmation(order))
    log_audit_event("subscription_checkout_paid_verified", user=user, request=request, metadata={
        "checkout_id": order.pk, "subscription_id": contract.pk,
    })
    return _orders().get(pk=order.pk)


class CheckoutVerifyView(_ProfessionalOnly):
    def post(self, request, transaction_id):
        role, org, criteria = _criteria(request.user)
        if not criteria:
            return error_response("Organisation professionnelle requise.", status_code=403)
        try:
            order = _orders().get(transaction_id=transaction_id, **criteria)
        except SubscriptionCheckout.DoesNotExist:
            return error_response("Commande inconnue.", status_code=404)
        try:
            updated = _sync_verified(order.pk, request=request, user=request.user)
        except (CheckoutConfigurationError, CheckoutProviderError):
            return error_response("Vérification du paiement indisponible. Aucune activation sans confirmation.", status_code=503)
        return success_response("État de paiement vérifié.", _serialize(updated))


class CheckoutNotificationView(APIView):
    """Public callback: accept only the transaction ID, then verify with CinetPay API."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return HttpResponse("OK", status=200)

    def post(self, request):
        external_id = request.data.get("cpm_trans_id")
        if not isinstance(external_id, str):
            return HttpResponse("OK", status=200)
        try:
            txn = uuid.UUID(hex=external_id)
        except (ValueError, AttributeError):
            return HttpResponse("OK", status=200)
        order = SubscriptionCheckout.objects.filter(transaction_id=txn).first()
        if order is None:
            return HttpResponse("OK", status=200)
        try:
            _sync_verified(order.pk, request=request)
        except (CheckoutProviderError, CheckoutConfigurationError, IntegrityError):
            # Retry callback or authenticated status refresh after temporary faults.
            return HttpResponse("Verification pending", status=503)
        return HttpResponse("OK", status=200)
