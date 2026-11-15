"""E32 · Superadmin enterprise portfolio, read-only, backed by actual records.

Only verified, revocable professional WebTokens can authenticate. No fabricated
companies, approval statuses, payments or publication credits are created.
"""
from datetime import timedelta

from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.posts.models import Application, Opportunity
from apps.api.v1.subscriptions.models import (
    BusinessSubscription, PublicationConsumption, SubscriptionTopUp,
)
from apps.api.v1.users.models import Enterprise
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


class SuperadminEnterpriseDirectoryE32(APIView):
    """Business partners and cumulative publication-credits, never account seats."""
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        search = str(request.query_params.get("search", "")).strip()[:120]
        status = str(request.query_params.get("status", "all")).strip()
        billing = str(request.query_params.get("billing", "all")).strip()
        if status not in ("all", "active", "inactive") or billing not in ("all", "active", "none"):
            return error_response("Filtre invalide.", status_code=400)
        try:
            page = int(request.query_params.get("page", 1))
            size = int(request.query_params.get("page_size", 12))
        except (ValueError, TypeError):
            return error_response("Pagination invalide.", status_code=400)
        if page < 1 or not 1 <= size <= 50:
            return error_response("Pagination invalide.", status_code=400)

        today = timezone.localdate()
        valid_contracts = BusinessSubscription.objects.filter(
            enterprise_id=OuterRef("pk"), quota_unit="publications",
            status__in=("active", "scheduled"),
            starts_at__lte=today, ends_at__gt=today,
        )
        companies = Enterprise.objects.select_related("user").annotate(
            subscribed=Exists(valid_contracts)
        )
        if search:
            companies = companies.filter(
                Q(company_name__icontains=search) | Q(sector__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__location__icontains=search)
            )
        if status != "all":
            companies = companies.filter(
                user__is_active=(status == "active"),
                user__is_banned=False,
            ) if status == "active" else companies.filter(
                Q(user__is_active=False) | Q(user__is_banned=True)
            )
        if billing != "all":
            companies = companies.filter(subscribed=(billing == "active"))
        companies = companies.order_by("company_name", "pk")
        count = companies.count()
        pages = max(1, (count + size - 1) // size)
        if page > pages:
            return error_response("Page inexistante.", status_code=404)
        page_companies = list(companies[(page - 1) * size:page * size])
        company_ids = [item.pk for item in page_companies]

        offer_counts = {
            entry["enterprise_id"]: entry
            for entry in Opportunity.objects.filter(
                enterprise_id__in=company_ids,
            ).values("enterprise_id").annotate(
                total=Count("pk"),
                open=Count(
                    "pk", filter=Q(status=Opportunity.Status.OPEN, post__is_archived=False,
                                   post__is_draft=False, post__is_hidden_by_admin=False),
                ),
            )
        }
        application_counts = {
            entry["opportunity__enterprise_id"]: entry["total"]
            for entry in Application.objects.filter(
                opportunity__enterprise_id__in=company_ids,
            ).values("opportunity__enterprise_id").annotate(total=Count("pk"))
        }
        active_contracts = list(BusinessSubscription.objects.filter(
            enterprise_id__in=company_ids, quota_unit="publications",
            status__in=("active", "scheduled"),
            starts_at__lte=today, ends_at__gt=today,
        ).order_by("-created_at", "-pk"))
        by_company = {}
        for contract in active_contracts:
            by_company.setdefault(contract.enterprise_id, contract)
        contract_ids = [contract.pk for contract in by_company.values()]
        topups = {
            item["subscription_id"]: item["total"] or 0
            for item in SubscriptionTopUp.objects.filter(
                subscription_id__in=contract_ids
            ).values("subscription_id").annotate(total=Sum("quantity"))
        }
        consumed = {
            item["subscription_id"]: item["total"]
            for item in PublicationConsumption.objects.filter(
                subscription_id__in=contract_ids
            ).values("subscription_id").annotate(total=Count("pk"))
        }

        def logo_url(company):
            try:
                return request.build_absolute_uri(company.logo.url) if company.logo else None
            except ValueError:
                return None

        rows = []
        for company in page_companies:
            user = company.user
            contract = by_company.get(company.pk)
            limit = contract.seats + topups.get(contract.pk, 0) if contract else 0
            used = consumed.get(contract.pk, 0) if contract else 0
            offers = offer_counts.get(company.pk, {})
            rows.append({
                "id": company.pk,
                "company_name": company.company_name,
                "sector": company.sector or "",
                "website": company.website or "",
                "logo_url": logo_url(company),
                "contact": {
                    "email": user.email,
                    "phone": user.phone_number or "",
                    "location": user.location or "",
                },
                "created_at": user.date_joined.isoformat(),
                "is_active": bool(user.is_active and not user.is_banned),
                "is_banned": bool(user.is_banned),
                "offers_count": offers.get("total", 0),
                "open_offers": offers.get("open", 0),
                "applications_count": application_counts.get(company.pk, 0),
                "subscription": {
                    "id": contract.pk,
                    "name": contract.offer_name,
                    "included": contract.seats,
                    "extra": topups.get(contract.pk, 0),
                    "capacity": limit,
                    "used": used,
                    "remaining": max(0, limit - used),
                    "expires_at": contract.ends_at.isoformat(),
                    "unit": "publications",
                } if contract else None,
            })

        all_companies = Enterprise.objects
        active_companies = all_companies.filter(user__is_active=True, user__is_banned=False)
        soon = today + timedelta(days=30)
        expiring_count = BusinessSubscription.objects.filter(
            enterprise__isnull=False, quota_unit="publications",
            status__in=("active", "scheduled"),
            starts_at__lte=today, ends_at__gt=today, ends_at__lte=soon,
        ).values("enterprise_id").distinct().count()
        summary = {
            "total": all_companies.count(),
            "active": active_companies.count(),
            "subscribed": all_companies.filter(Exists(valid_contracts)).count(),
            "expiring_30_days": expiring_count,
        }
        return success_response("Annuaire des entreprises.", {
            "summary": summary, "results": rows, "count": count,
            "page": page, "page_size": size, "pages": pages,
        })
