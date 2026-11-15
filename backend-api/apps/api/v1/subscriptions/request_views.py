"""Web-only commercial requests: organisation submission and MFA-protected review.

An approval records a commercial decision. It never invents a payment, modifies
an immutable contract, or grants capacity without the existing explicit workflow.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication
from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import Enterprise
from .models import BusinessSubscription, SubscriptionChangeRequest
from .quotas import current_contract, quota_summary
from .views import _organisation_for


def _serialize(item):
    organisation_type = "enterprise" if item.enterprise_id else "institution"
    owner = item.enterprise if item.enterprise_id else item.institution
    label = owner.company_name if item.enterprise_id else owner.name
    contract = item.source_subscription
    today = timezone.localdate()
    live = bool(contract and contract.status == "active" and contract.starts_at <= today < contract.ends_at)
    return {
        "id": item.pk, "organisation_type": organisation_type,
        "organisation_id": owner.pk, "organisation_name": label,
        "request_type": item.request_type, "status": item.status,
        "requested_term_months": item.requested_term_months,
        "requested_quantity": item.requested_quantity,
        "note": item.note, "admin_note": item.admin_note,
        "source_subscription_id": item.source_subscription_id,
        "current_capacity": contract.seats if contract else None,
        "current_offer_name": contract.offer_name if contract else None,
        "current_quota": quota_summary(contract) if live else None,
        "current_ends_at": contract.ends_at.isoformat() if contract else None,
        "created_at": item.created_at.isoformat(),
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "requires_manual_activation": True,
    }


def _queryset():
    return SubscriptionChangeRequest.objects.select_related(
        "institution", "enterprise", "source_subscription",
    )


class _ProfessionalWebOnly(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


class MySubscriptionRequestsView(_ProfessionalWebOnly):
    """GET/POST: only this authenticated enterprise or institution may request change."""
    def get(self, request):
        role, org = _organisation_for(request.user)
        if not org or role not in ("enterprise", "institution"):
            return error_response("Organisation professionnelle requise.", status_code=403)
        criteria = {"enterprise": org} if role == "enterprise" else {"institution": org}
        items = _queryset().filter(**criteria)[:50]
        return success_response("Vos demandes commerciales.", [_serialize(i) for i in items])

    def post(self, request):
        role, org = _organisation_for(request.user)
        if not org or role not in ("enterprise", "institution"):
            return error_response("Organisation professionnelle requise.", status_code=403)
        request_type = request.data.get("request_type")
        if request_type not in ("renewal", "capacity"):
            return error_response("Type de demande invalide.")
        note = request.data.get("note", "")
        if not isinstance(note, str) or len(note.strip()) > 500:
            return error_response("Message trop long ou invalide.")
        term = quantity = None
        if request_type == "renewal":
            raw = request.data.get("requested_term_months")
            if type(raw) not in (str, int) or str(raw) not in ("1", "6", "12"):
                return error_response("Choisissez 1, 6 ou 12 mois.")
            term = int(raw)
        else:
            raw = request.data.get("requested_quantity")
            if type(raw) not in (str, int) or not str(raw).isdigit() or not (1 <= int(raw) <= 1000000):
                return error_response("Indiquez une capacité positive (maximum 1 000 000).")
            quantity = int(raw)
        criteria = {"enterprise": org} if role == "enterprise" else {"institution": org}
        with transaction.atomic():
            # Serialise requests per organisation to prevent duplicate pending submissions.
            if role == "enterprise":
                Enterprise.objects.select_for_update().get(pk=org.pk)
            else:
                Institution.objects.select_for_update().get(pk=org.pk)
            if SubscriptionChangeRequest.objects.filter(
                **criteria, request_type=request_type, status="pending",
            ).exists():
                return error_response(
                    "Une demande de ce type est déjà en attente.", status_code=409,
                )
            contract = current_contract(
                enterprise=org if role == "enterprise" else None,
                institution=org if role == "institution" else None,
                lock=True,
            )
            if request_type == "capacity" and contract is None:
                return error_response(
                    "Un abonnement actif est requis pour une extension de capacité.",
                    status_code=409,
                )
            item = SubscriptionChangeRequest.objects.create(
                **criteria, source_subscription=contract,
                request_type=request_type, requested_term_months=term,
                requested_quantity=quantity, note=note.strip(),
                created_by=request.user,
            )
        log_audit_event("subscription_request_created", user=request.user, request=request, metadata={
            "request_id": item.pk, "request_type": item.request_type, "organisation_type": role,
        })
        item = _queryset().get(pk=item.pk)
        return success_response(
            "Demande transmise au Superadmin. Aucun paiement n'a été effectué.",
            _serialize(item), status_code=201,
        )


class SuperadminSubscriptionRequestsView(_ProfessionalWebOnly):
    """GET: full commercial queue, accessible exclusively to MFA-verified superadmins."""
    def get(self, request):
        if request.user.role != "superAdmin" or not request.user.is_active or request.user.is_banned:
            return error_response("Superadmin requis.", status_code=403)
        audience = request.query_params.get("audience")
        if audience and audience not in ("enterprise", "institution"):
            return error_response("Filtre inconnu.")
        items = _queryset()
        if audience == "enterprise":
            items = items.filter(enterprise__isnull=False)
        elif audience == "institution":
            items = items.filter(institution__isnull=False)
        return success_response("Demandes commerciales.", [_serialize(i) for i in items[:200]])


class SuperadminSubscriptionRequestDetailView(_ProfessionalWebOnly):
    """PATCH: recorded review, with manual subscription/capacity fulfillment afterward."""
    def patch(self, request, request_id):
        if request.user.role != "superAdmin" or not request.user.is_active or request.user.is_banned:
            return error_response("Superadmin requis.", status_code=403)
        decision = request.data.get("status")
        if decision not in ("approved", "rejected", "info_requested"):
            return error_response("Décision invalide.")
        note = request.data.get("admin_note", "")
        if not isinstance(note, str) or len(note.strip()) > 500:
            return error_response("Commentaire invalide.")
        note = note.strip()
        if decision in ("rejected", "info_requested") and not note:
            return error_response("Un motif est obligatoire pour ce choix.")
        with transaction.atomic():
            try:
                item = _queryset().select_for_update().get(pk=request_id)
            except SubscriptionChangeRequest.DoesNotExist:
                return error_response("Demande introuvable.", status_code=404)
            if item.status not in ("pending", "info_requested"):
                return error_response("Cette demande a déjà été traitée.", status_code=409)
            item.status = decision
            item.admin_note = note
            item.reviewed_by = request.user
            item.reviewed_at = timezone.now()
            item.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at"])
        log_audit_event("subscription_request_reviewed", user=request.user, request=request, metadata={
            "request_id": item.pk, "decision": decision,
        })
        return success_response(
            "Décision enregistrée. Attribution ou extension manuelle requise, sans paiement implicite.",
            _serialize(item),
        )
