"""E61 | Read-only, MFA-only Superadmin audit observatory.

This intentionally returns a strictly allowlisted view of AuditLogEntry.
Historic metadata may contain tokens, email addresses or PII: neither raw
metadata nor raw IP addresses are ever sent to the browser. No migration.
"""
from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.models import AuditLogEntry
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication

PERIODS = (7, 30, 90, 180)
CATEGORIES = ("all", "access", "invitations", "moderation", "operations", "other")

ACCESS = {
    "login_success", "login_failed", "logout", "password_changed",
    "sessions_revoked", "mfa_challenge_issued", "mfa_success",
}
INVITATIONS = {"invitation_sent", "invitation_revoked", "invitation_accepted"}
MODERATION = {"report_reviewed", "post_hidden", "user_banned", "user_unbanned"}
OPERATIONS = {
    "import_completed", "account_deleted", "privacy_updated", "data_exported",
    "api_key_created", "api_key_revoked",
}
FAILURES = {"login_failed"}
KNOWN = ACCESS | INVITATIONS | MODERATION | OPERATIONS
ACTION_LABELS = dict(AuditLogEntry.ACTION_CHOICES)

# Only numbers and vetted enum values. Never copy raw strings from metadata:
# old events may contain a token, e-mail, device fingerprint, password etc.
SAFE_INT_FIELDS = (
    "report_id", "post_id", "job_id", "institution_id", "enterprise_id",
    "user_id", "total", "success", "errors", "count",
)
SAFE_ENUM_FIELDS = {
    "outcome": {"pending", "dismissed", "actioned"},
    "import_type": {"students", "alumni", "promotions", "establishments"},
    "organisation_type": {"institution", "enterprise"},
}


def _category(action):
    if action in ACCESS:
        return "access"
    if action in INVITATIONS:
        return "invitations"
    if action in MODERATION:
        return "moderation"
    if action in OPERATIONS:
        return "operations"
    return "other"


def _safe_metadata(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key in SAFE_INT_FIELDS:
        val = value.get(key)
        if isinstance(val, int) and not isinstance(val, bool) and 0 <= val <= 2**63 - 1:
            result[key] = val
    for key, allowed in SAFE_ENUM_FIELDS.items():
        if isinstance(value.get(key), str) and value[key] in allowed:
            result[key] = value[key]
    return result


def _row(item):
    owner = item.user
    return {
        "id": item.pk,
        "action": item.action,
        "label": ACTION_LABELS.get(item.action, "Événement enregistré"),
        "category": _category(item.action),
        "actor": (owner.get_full_name().strip() or owner.username) if owner else "Compte supprimé ou système",
        "actor_role": owner.role if owner else None,
        "actor_id": owner.pk if owner else None,
        "created_at": item.created_at.isoformat(),
        "details": _safe_metadata(item.metadata),
    }


def _grain(days):
    return "day" if days == 7 or days == 30 else "week" if days == 90 else "month"


def _bucket(date, grain):
    if isinstance(date, datetime):
        date = date.date()
    if grain == "week":
        return date - timedelta(days=date.weekday())
    if grain == "month":
        return date.replace(day=1)
    return date


def _buckets(first, last, grain):
    cur, end = _bucket(first, grain), _bucket(last, grain)
    dates = []
    while cur <= end:
        dates.append(cur)
        if grain == "day":
            cur += timedelta(days=1)
        elif grain == "week":
            cur += timedelta(days=7)
        else:
            cur = cur.replace(year=cur.year + (cur.month == 12), month=cur.month % 12 + 1)
    return dates


class SuperadminAuditDirectoryE61(APIView):
    """GET /api/v1/backoffice/audit-v2/ (never writes audit events)."""

    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", "30"))
            page = int(request.query_params.get("page", "1"))
            size = int(request.query_params.get("page_size", "12"))
        except (TypeError, ValueError):
            return error_response("Paramètres numériques invalides.", status_code=400)
        if days not in PERIODS or page < 1 or size not in (12, 24, 48):
            return error_response("Période ou pagination invalide.", status_code=400)

        category = str(request.query_params.get("category", "all")).strip()
        action = str(request.query_params.get("action", "all")).strip()
        search = str(request.query_params.get("search", "")).strip()[:100]
        if category not in CATEGORIES or (action != "all" and action not in ACTION_LABELS):
            return error_response("Filtre invalide.", status_code=400)

        today = timezone.localdate()
        first = today - timedelta(days=days - 1)
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(first, time.min), tz)
        end = timezone.make_aware(
            datetime.combine(today + timedelta(days=1), time.min), tz,
        )
        period = AuditLogEntry.objects.filter(created_at__gte=start, created_at__lt=end)
        summary = {
            "events": period.count(),
            "invitations": period.filter(action__in=INVITATIONS).count(),
            "moderation": period.filter(action__in=MODERATION).count(),
            "access": period.filter(action__in=ACCESS).count(),
            "operations": period.filter(action__in=OPERATIONS).count(),
            "other": period.exclude(action__in=KNOWN).count(),
            "failed_access": period.filter(action__in=FAILURES).count(),
        }

        grain = _grain(days)
        bins = _buckets(first, today, grain)
        func = {"day": TruncDate, "week": TruncWeek, "month": TruncMonth}[grain]
        sums = period.annotate(slot=func("created_at")).values("slot").annotate(
            count=Count("pk"),
        ).order_by()
        by_date = {_bucket(row["slot"], grain): row["count"] for row in sums}

        qs = period.select_related("user")
        if category == "access":
            qs = qs.filter(action__in=ACCESS)
        elif category == "invitations":
            qs = qs.filter(action__in=INVITATIONS)
        elif category == "moderation":
            qs = qs.filter(action__in=MODERATION)
        elif category == "operations":
            qs = qs.filter(action__in=OPERATIONS)
        elif category == "other":
            qs = qs.exclude(action__in=KNOWN)
        if action != "all":
            qs = qs.filter(action=action)
        if search:
            matching_labels = [
                key for key, label in ACTION_LABELS.items()
                if search.casefold() in label.casefold()
            ]
            qs = qs.filter(
                Q(user__username__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(action__icontains=search)
                | Q(action__in=matching_labels)
            )
        total = qs.count()
        pages = max(1, (total + size - 1) // size)
        if page > pages:
            return error_response("Page inexistante.", status_code=404)
        entries = qs.order_by("-created_at", "-pk")[(page - 1) * size:page * size]

        response = success_response("Journal d'audit sécurisé.", {
            "days": days, "since": first.isoformat(), "until": today.isoformat(),
            "summary": summary,
            "action_choices": [
                {"value": action_id, "label": label}
                for action_id, label in AuditLogEntry.ACTION_CHOICES
            ],
            "trend": {
                "granularity": grain,
                "labels": [date.isoformat() for date in bins],
                "events": [by_date.get(date, 0) for date in bins],
            },
            "page": page, "pages": pages, "page_size": size,
            "count": total,
            "results": [_row(entry) for entry in entries],
        })
        response["Cache-Control"] = "no-store"
        return response
