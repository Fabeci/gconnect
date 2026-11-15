"""E36 · Superadmin finance read model.

This is NOT an invoice ledger. Only provider-verified checkouts can be counted
as paid. Manual subscriptions are intentionally excluded from receipts.
No invoice number, PDF, tax amount, or payment proof is synthesized here.
"""
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import success_response
from apps.api.v1.subscriptions.models import SubscriptionCheckout
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


def _verified():
    return SubscriptionCheckout.objects.filter(
        status=SubscriptionCheckout.Status.PAID,
        verified_at__isnull=False,
        activated_subscription__isnull=False,
    )


def _serialize(order):
    owner_type = "enterprise" if order.enterprise_id else "institution"
    owner = order.enterprise if order.enterprise_id else order.institution
    organisation_name = (
        owner.company_name if owner_type == "enterprise" else owner.name
    ) if owner is not None else "Organisation indisponible"
    verified = (
        order.status == SubscriptionCheckout.Status.PAID
        and order.verified_at is not None
        and order.activated_subscription_id is not None
    )
    invoice = getattr(order, "issued_invoice", None)
    return {
        "id": order.pk,
        "invoice_id": invoice.pk if invoice is not None else None,
        "invoice_number": invoice.number if invoice is not None else None,
        "transaction_id": str(order.transaction_id),
        "organisation_type": owner_type,
        "organisation_name": organisation_name,
        "offer_name": order.offer_name,
        "capacity": order.capacity,
        "quota_unit": order.quota_unit,
        "term_months": order.term_months,
        "amount": str(order.amount),
        "currency": order.currency,
        "status": order.status,
        "provider": order.provider,
        "is_verified": verified,
        "created_at": order.created_at.isoformat(),
        "verified_at": order.verified_at.isoformat() if verified else None,
        "subscription_id": order.activated_subscription_id if verified else None,
    }


class SuperadminFinanceRegisterE36(APIView):
    """Read-only, MFA-bound view of real online checkout events."""
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        base = SubscriptionCheckout.objects.all()
        verified = _verified()
        paid_count = verified.count()
        paid_xof = verified.filter(currency="XOF").aggregate(total=Sum("amount"))["total"]
        totals = {
            "paid": paid_count,
            "pending": base.filter(status="pending").count(),
            "failed": base.filter(status="failed").count(),
            "canceled": base.filter(status="canceled").count(),
            "unverified_paid": base.filter(
                status="paid",
            ).exclude(
                verified_at__isnull=False,
                activated_subscription__isnull=False,
            ).count(),
            "total": base.count(),
            "verified_total_xof": str(paid_xof if paid_xof is not None else Decimal("0.00")),
            "invoicing_available": False,
        }
        status = request.query_params.get("status", "all")
        search = request.query_params.get("search", "").strip()
        if status not in ("all", "paid", "pending", "failed", "canceled"):
            status = "all"
        if status == "paid":
            rows = verified
        elif status != "all":
            rows = base.filter(status=status)
        else:
            rows = base
        if search:
            rows = rows.filter(
                Q(enterprise__company_name__icontains=search[:100])
                | Q(institution__name__icontains=search[:100])
                | Q(offer_name__icontains=search[:100])
            )
            # Avoid exposing raw lookup errors for arbitrary UUID fragments.
            try:
                import uuid
                txn = uuid.UUID(search)
            except (ValueError, AttributeError):
                txn = None
            if txn is not None:
                rows = (verified if status == "paid" else base.filter(status=status)
                        if status != "all" else base).filter(
                    Q(enterprise__company_name__icontains=search[:100])
                    | Q(institution__name__icontains=search[:100])
                    | Q(offer_name__icontains=search[:100])
                    | Q(transaction_id=txn)
                )
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        paginator = Paginator(rows.select_related(
            "enterprise", "institution", "activated_subscription", "issued_invoice",
        ).order_by("-created_at", "-pk"), 20)
        selected = paginator.get_page(page)
        response = success_response("Registre réel des paiements G-Connect.", {
            "summary": totals,
            "results": [_serialize(item) for item in selected],
            "count": paginator.count,
            "page": selected.number,
            "pages": paginator.num_pages,
            "status": status,
        })
        response["Cache-Control"] = "no-store"
        return response
