"""E60 | Global, factual Superadmin analytics.

Read-only audited-source counters and bounded historical trends. It never
invent stats, uses no demo rows and exposes no individual account details.
The existing /backoffice/stats/ endpoint remains unchanged for other clients.
"""
from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.backoffice.models import Report
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.establishments.models import Institution
from apps.api.v1.posts.models import Application, Comment, Post, Reaction
from apps.api.v1.subscriptions.models import BusinessSubscription
from apps.api.v1.users.models import Enterprise, User
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


PERIODS = {30, 90, 180, 365}
ROLE_KEYS = ("student", "alumni", "enterprise", "etablissement", "superAdmin")
CONTENT_KEYS = (
    Post.PostType.OPPORTUNITY, Post.PostType.EVENT, Post.PostType.PROJECT,
    Post.PostType.DISCUSSION, Post.PostType.SHARE,
)


def _bucket(date, granularity):
    if isinstance(date, datetime):
        date = date.date()
    if granularity == "day":
        return date
    if granularity == "week":
        return date - timedelta(days=date.weekday())
    return date.replace(day=1)


def _period_grid(start_day, end_day, granularity):
    current = _bucket(start_day, granularity)
    stop = _bucket(end_day, granularity)
    result = []
    while current <= stop:
        result.append(current)
        if granularity == "day":
            current += timedelta(days=1)
        elif granularity == "week":
            current += timedelta(days=7)
        else:
            current = current.replace(
                year=current.year + (current.month == 12),
                month=current.month % 12 + 1,
                day=1,
            )
    return result


def _trend(queryset, field, start_time, end_time, grain, bins):
    # Each grouped row is a single SQL query; gaps are actual zeros, never
    # fabricated events. Do not load model instances or personal information.
    trunc = {"day": TruncDate, "week": TruncWeek, "month": TruncMonth}[grain]
    groups = (
        queryset.filter(**{field + "__gte": start_time, field + "__lt": end_time})
        .annotate(e60_slot=trunc(field))
        .values("e60_slot")
        .annotate(total=Count("pk"))
        .order_by()
    )
    mapped = {_bucket(row["e60_slot"], grain): row["total"] for row in groups}
    return [mapped.get(day, 0) for day in bins]


class SuperadminStatisticsE60(APIView):
    """GET /api/v1/backoffice/statistics-v2/?days=30|90|180|365"""

    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", "180"))
        except (ValueError, TypeError):
            return error_response("Période invalide.", status_code=400)
        if days not in PERIODS:
            return error_response("Période invalide.", status_code=400)

        today = timezone.localdate()
        first_day = today - timedelta(days=days - 1)
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(first_day, time.min), tz)
        end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min), tz)
        previous_start = start - timedelta(days=days)
        grain = "day" if days == 30 else "week" if days == 90 else "month"
        bins = _period_grid(first_day, today, grain)

        registered = User.objects.all()
        posts = Post.objects.all()
        institutions = Institution.objects.all()
        enterprises = Enterprise.objects.all()

        new_accounts = registered.filter(date_joined__gte=start, date_joined__lt=end).count()
        preceding = registered.filter(
            date_joined__gte=previous_start, date_joined__lt=start,
        ).count()
        # Percentage is undefined when there is no prior baseline.
        growth_percent = (
            round((new_accounts - preceding) * 100 / preceding, 1)
            if preceding else None
        )
        active_enterprises = enterprises.filter(
            is_active=True, verified_at__isnull=False,
        ).count()
        company_total = enterprises.count()
        active_institutions = institutions.filter(is_active=True).count()
        role_counts = dict(
            registered.values("role").annotate(total=Count("pk")).values_list("role", "total")
        )
        post_counts = dict(
            posts.values("post_type").annotate(total=Count("pk"))
            .values_list("post_type", "total")
        )
        summary = {
            "new_accounts": new_accounts,
            "previous_accounts": preceding,
            "growth_percent": growth_percent,
            "accounts_total": registered.count(),
            "accounts_active": registered.filter(is_active=True, is_banned=False).count(),
            "accounts_banned": registered.filter(is_banned=True).count(),
            "institutions_total": institutions.count(),
            "institutions_active": active_institutions,
            "enterprises_total": company_total,
            "enterprises_verified": active_enterprises,
            "posts_total": posts.count(),
            "posts_published": posts.filter(
                is_hidden_by_admin=False, is_draft=False, is_archived=False,
            ).count(),
            "posts_hidden": posts.filter(is_hidden_by_admin=True).count(),
            "comments_total": Comment.objects.count(),
            "reactions_total": Reaction.objects.count(),
            "applications_total": Application.objects.count(),
            "reports_pending": Report.objects.filter(status=Report.Status.PENDING).count(),
            # Active only when the subscription is currently valid.
            "subscriptions_active": BusinessSubscription.objects.filter(
                status=BusinessSubscription.State.ACTIVE,
                starts_at__lte=today, ends_at__gte=today,
            ).count(),
        }

        response = success_response("Statistiques globales réelles.", {
            "days": days,
            "since": first_day.isoformat(),
            "until": today.isoformat(),
            "granularity": grain,
            "summary": summary,
            "roles": {key: role_counts.get(key, 0) for key in ROLE_KEYS},
            "contents": {key: post_counts.get(key, 0) for key in CONTENT_KEYS},
            "trend": {
                "labels": [day.isoformat() for day in bins],
                "accounts": _trend(registered, "date_joined", start, end, grain, bins),
                "posts": _trend(posts, "created_at", start, end, grain, bins),
                "institutions": _trend(institutions, "created_at", start, end, grain, bins),
                # Enterprise has no creation timestamp. Use owner registration
                # as a proxy, clearly labelled as such on the interface.
                "enterprise_accounts": _trend(
                    enterprises, "user__date_joined", start, end, grain, bins,
                ),
            },
            "sources": {
                "accounts": "User.date_joined",
                "posts": "Post.created_at",
                "institutions": "Institution.created_at",
                "enterprise_accounts": "Enterprise.user.date_joined",
            },
        })
        response["Cache-Control"] = "no-store"
        return response
