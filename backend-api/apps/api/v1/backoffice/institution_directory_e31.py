"""E31 · Dedicated, read-only academic partner directory for the MFA-verified Superadmin.

No artificial institutions, verification statuses, or payments. The list is
paginated, includes both active and inactive institutions, and computes school
account consumption from real membership seat flags. Enterprise roles cannot
query this endpoint.
"""
from datetime import timedelta

from django.db.models import Exists, OuterRef, Q, Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import success_response, error_response
from apps.api.v1.establishments.models import Institution, StudentInstitution, AlumniInstitution
from apps.api.v1.subscriptions.models import BusinessSubscription
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


class SuperadminInstitutionDirectoryE31(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        search = str(request.query_params.get("search", "")).strip()[:100]
        status = str(request.query_params.get("status", "all")).strip()
        billing = str(request.query_params.get("billing", "all")).strip()
        if status not in ("all", "active", "inactive") or billing not in ("all", "active", "none"):
            return error_response("Filtre invalide.", status_code=400)
        try:
            page = int(request.query_params.get("page", "1"))
            size = int(request.query_params.get("page_size", "12"))
        except (TypeError, ValueError):
            return error_response("Pagination invalide.", status_code=400)
        if page < 1 or not 1 <= size <= 50:
            return error_response("Pagination invalide.", status_code=400)

        today = timezone.localdate()
        live_contracts = BusinessSubscription.objects.filter(
            institution_id=OuterRef("pk"),
            status="active",
            quota_unit="accounts",
            starts_at__lte=today,
            ends_at__gt=today,
        )
        query = Institution.objects.select_related("city", "country").annotate(
            subscribed=Exists(live_contracts)
        )
        if search:
            query = query.filter(Q(name__icontains=search) | Q(acronym__icontains=search)
                                 | Q(city__name__icontains=search)
                                 | Q(country__name__icontains=search))
        if status != "all":
            query = query.filter(is_active=(status == "active"))
        if billing != "all":
            query = query.filter(subscribed=(billing == "active"))
        query = query.order_by("name", "pk")
        filtered_total = query.count()
        pages = max(1, (filtered_total + size - 1) // size)
        if page > pages:
            return error_response("Page inexistante.", status_code=404)
        slice_start = (page - 1) * size
        schools = list(query[slice_start:slice_start + size])
        ids = [school.pk for school in schools]

        def membership_totals(model, **filters):
            return {
                entry["institution_id"]: entry["total"]
                for entry in model.objects.filter(
                    institution_id__in=ids, **filters
                ).values("institution_id").annotate(total=Count("pk"))
            }
        students = membership_totals(StudentInstitution)
        alumni = membership_totals(AlumniInstitution)
        active_students = membership_totals(StudentInstitution, seat_enabled=True)
        active_alumni = membership_totals(AlumniInstitution, seat_enabled=True)

        subscriptions = BusinessSubscription.objects.filter(
            institution_id__in=ids, status="active", quota_unit="accounts",
            starts_at__lte=today, ends_at__gt=today,
        ).order_by("-created_at", "-pk")
        live_by_school = {}
        for item in subscriptions:
            live_by_school.setdefault(item.institution_id, item)

        def image_url(school):
            try:
                return request.build_absolute_uri(school.logo.url) if school.logo else None
            except ValueError:
                return None

        results = []
        for school in schools:
            contract = live_by_school.get(school.pk)
            consumed = active_students.get(school.pk, 0) + active_alumni.get(school.pk, 0)
            results.append({
                "id": school.pk,
                "name": school.name,
                "acronym": school.acronym or "",
                "logo_url": image_url(school),
                "description": school.description or "",
                "city": school.city.name if school.city_id else "",
                "country": school.country.name if school.country_id else "",
                "address": school.address or "",
                "email": school.email or "",
                "phone": school.phone or "",
                "website": school.website or "",
                "accreditation": school.accreditation or "",
                "established_year": school.established_year,
                "created_at": school.created_at.isoformat(),
                "is_active": school.is_active,
                "members_count": students.get(school.pk, 0) + alumni.get(school.pk, 0),
                "active_accounts": consumed,
                "subscription": {
                    "id": contract.pk,
                    "name": contract.offer_name,
                    "capacity": contract.seats,
                    "expires_at": contract.ends_at.isoformat(),
                    "remaining": max(0, contract.seats - consumed),
                    "status": "active",
                } if contract else None,
            })
        all_schools = Institution.objects
        subscribed_count = Institution.objects.filter(
            Exists(live_contracts)
        ).count()
        expiring_at = today + timedelta(days=30)
        expiring_count = BusinessSubscription.objects.filter(
            institution__isnull=False, status="active", quota_unit="accounts",
            starts_at__lte=today, ends_at__gt=today, ends_at__lte=expiring_at,
        ).values("institution_id").distinct().count()
        summary = {
            "total": all_schools.count(),
            "active": all_schools.filter(is_active=True).count(),
            "inactive": all_schools.filter(is_active=False).count(),
            "subscribed": subscribed_count,
            "expiring_30_days": expiring_count,
        }
        return success_response("Annuaire des établissements.", {
            "summary": summary, "results": results, "count": filtered_total,
            "page": page, "page_size": size, "pages": pages,
        })
