"""Authoritative organisation quotas. All write paths lock the organisation row.

Publications are one-time consumables per contract: deletion, closing, or
archiving a post does not reverse its ledger entry. School seats are concurrent
active members, independent of their news-feed visibility preference.
"""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.api.v1.establishments.models import AlumniInstitution, Institution, StudentInstitution
from apps.api.v1.users.models import Enterprise

from .models import BusinessSubscription, PublicationConsumption


class QuotaExceeded(APIException):
    """Expected business denial; endpoints translate it into HTTP 409."""
    status_code = 409
    default_code = "subscription_quota"
    default_detail = "Quota de l'abonnement atteint."


def current_contract(*, enterprise=None, institution=None, lock=False):
    if (enterprise is None) == (institution is None):
        raise ValueError("Exactly one organisation is required.")
    today = timezone.localdate()
    contracts = BusinessSubscription.objects.filter(
        status__in=[BusinessSubscription.State.ACTIVE, BusinessSubscription.State.SCHEDULED],
        starts_at__lte=today, ends_at__gt=today,
    )
    contracts = contracts.filter(enterprise=enterprise) if enterprise is not None else contracts.filter(institution=institution)
    if lock:
        contracts = contracts.select_for_update()
    return contracts.select_related("price_option__offer").first()


def total_allowance(contract):
    extras = contract.top_ups.aggregate(total=Sum("quantity"))["total"] or 0
    return contract.seats + extras


def active_institution_accounts(institution):
    """Count enabled, activated students and alumni; do not use feed is_active."""
    students = StudentInstitution.objects.filter(
        institution=institution, seat_enabled=True, student__user__is_active=True,
    ).count()
    alumni = AlumniInstitution.objects.filter(
        institution=institution, seat_enabled=True, alumni__user__is_active=True,
    ).count()
    return students + alumni


def quota_summary(contract):
    capacity = total_allowance(contract)
    if contract.quota_unit == "publications":
        used = contract.publication_consumptions.count()
    elif contract.institution_id:
        used = active_institution_accounts(contract.institution)
    else:
        # Grandfathered pre-E25 enterprise contracts were based on 'seats'.
        # Do not silently reinterpret them as purchased publications.
        used = 0
    return {
        "unit": contract.quota_unit, "included": contract.seats,
        "extra": capacity - contract.seats, "limit": capacity,
        "used": used, "remaining": max(0, capacity - used),
        "exhausted": used >= capacity,
    }


@transaction.atomic
def consume_enterprise_publication(enterprise, post):
    """Charge once, at the first actual publication, even if the post is later deleted."""
    if post.is_draft:
        return
    Enterprise.objects.select_for_update().get(pk=enterprise.pk)
    if PublicationConsumption.objects.filter(post=post).exists():
        return
    contract = current_contract(enterprise=enterprise, lock=True)
    if contract is None or contract.quota_unit != "publications":
        raise QuotaExceeded("Aucun abonnement Publications valide. Choisissez une offre Entreprise.")
    if contract.publication_consumptions.count() >= total_allowance(contract):
        raise QuotaExceeded("Quota de publications atteint. Ajoutez un pack ou renouvelez votre abonnement.")
    PublicationConsumption.objects.create(
        subscription=contract, post=post, title_snapshot=post.title,
    )


def require_available_school_seat(institution):
    """Caller holds the institution row lock and an atomic transaction."""
    contract = current_contract(institution=institution, lock=True)
    if contract is None or contract.quota_unit != "accounts":
        raise QuotaExceeded("Aucun abonnement Comptes valide. Contactez votre établissement.")
    if active_institution_accounts(institution) >= total_allowance(contract):
        raise QuotaExceeded("Limite de comptes actifs atteinte. Augmentez la capacité de l'établissement.")


def lock_institution(institution_id):
    return Institution.objects.select_for_update().get(pk=institution_id)
