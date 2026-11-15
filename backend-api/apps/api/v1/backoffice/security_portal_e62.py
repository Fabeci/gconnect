"""E62 | Security & sessions observatory for the authenticated Superadmin.

Real, global aggregate security posture and *own* browser sessions only.
No access to another user's device list, IP, user-agent string, tokens or MFA
secrets. Revocation is explicit, limited to one's own *other* web session.
No model change and no migration.
"""
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncWeek
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.users.models import (
    EstablishmentWebSession, LoginAttempt, PrivilegedMFADevice,
    PrivilegedRecoveryCode, User,
)
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication

PERIODS = (7, 30, 90)
ROLES = ("superAdmin", "etablissement", "enterprise")


def _live(now):
    idle_cutoff = now - timedelta(minutes=settings.ESTABLISHMENT_WEB_SESSION_IDLE_MINUTES)
    return EstablishmentWebSession.objects.filter(
        revoked_at__isnull=True, expires_at__gt=now,
        last_seen_at__gt=idle_cutoff,
    )


def _device(user_agent):
    """Only general hints, never the raw user-agent or its unique fingerprint."""
    value = str(user_agent or "").lower()
    if "edg/" in value or "edge/" in value:
        browser = "Edge"
    elif "firefox" in value or "fxios/" in value:
        browser = "Firefox"
    elif "chrome/" in value or "crios/" in value:
        browser = "Chrome"
    elif "safari/" in value:
        browser = "Safari"
    else:
        browser = "Autre"

    if "iphone" in value or "ipad" in value or "ios" in value:
        os = "iOS"
    elif "android" in value:
        os = "Android"
    elif "windows" in value:
        os = "Windows"
    elif "mac os" in value or "macintosh" in value:
        os = "macOS"
    elif "linux" in value:
        os = "Linux"
    else:
        os = "Autre"

    if "ipad" in value or "tablet" in value:
        kind = "tablette"
    elif "mobile" in value or "iphone" in value or "android" in value:
        kind = "mobile"
    elif os in ("Windows", "macOS", "Linux"):
        kind = "ordinateur"
    else:
        kind = "inconnu"
    return {"browser": browser, "os": os, "kind": kind}


def _own(row, current_id):
    return {
        "id": row.pk,
        "current": row.pk == current_id,
        "device": _device(row.user_agent),
        "created_at": row.created_at.isoformat(),
        "last_seen_at": row.last_seen_at.isoformat(),
        "expires_at": row.expires_at.isoformat(),
    }


class _SecurityBase(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    @staticmethod
    def ok(message, data):
        response = success_response(message, data)
        response["Cache-Control"] = "no-store"
        return response


class SuperadminSecurityDirectoryE62(_SecurityBase):
    """GET: organization-wide metrics and only the actor's live web devices."""

    def get(self, request):
        try:
            days = int(request.query_params.get("days", "30"))
        except (TypeError, ValueError):
            return error_response("Période invalide.", status_code=400)
        if days not in PERIODS:
            return error_response("Période invalide.", status_code=400)

        now = timezone.now()
        today = timezone.localdate()
        first = today - timedelta(days=days - 1)
        tz = timezone.get_current_timezone()
        begin = timezone.make_aware(datetime.combine(first, time.min), tz)
        end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min), tz)
        grain = "day" if days < 90 else "week"

        # Avoid a cached/stale last_seen session being represented as active.
        live = _live(now)
        professionals = User.objects.filter(is_active=True, is_banned=False, role__in=ROLES)
        mfa_enrolled = PrivilegedMFADevice.objects.filter(
            user__in=professionals, confirmed_at__isnull=False,
        ).count()
        professional_count = professionals.count()
        owner_sessions = list(live.filter(user=request.user).order_by("-created_at", "-pk")[:20])
        remaining = PrivilegedRecoveryCode.objects.filter(
            user=request.user, used_at__isnull=True,
        ).count()

        # LoginAttempt is a log of recorded attempts, not exhaustive security telemetry.
        attempts = LoginAttempt.objects.filter(
            created_at__gte=begin, created_at__lt=end,
        )
        grain_func = TruncDate if grain == "day" else TruncWeek
        grouped = (
            attempts.annotate(slot=grain_func("created_at"))
            .values("slot").annotate(
                successful=Count("pk", filter=Q(success=True)),
                failed=Count("pk", filter=Q(success=False)),
            ).order_by()
        )
        def bucket(value):
            d = value.date() if isinstance(value, datetime) else value
            return d - timedelta(days=d.weekday()) if grain == "week" else d
        observed = {bucket(row["slot"]): row for row in grouped}
        dates = []
        day = bucket(first)
        through = bucket(today)
        while day <= through:
            dates.append(day)
            day += timedelta(days=7 if grain == "week" else 1)

        return self.ok("État de sécurité de la plateforme.", {
            "days": days,
            "since": first.isoformat(),
            "until": today.isoformat(),
            "summary": {
                "sessions_active": live.count(),
                "professionals_active": professional_count,
                "mfa_enabled": mfa_enrolled,
                "mfa_pending": professional_count - mfa_enrolled,
                "failures": attempts.filter(success=False).count(),
                "successes": attempts.filter(success=True).count(),
                "revoked_7d": EstablishmentWebSession.objects.filter(
                    revoked_at__gte=now - timedelta(days=7), revoked_at__lte=now,
                ).count(),
                "expiring_24h": live.filter(
                    expires_at__lte=now + timedelta(hours=24),
                ).count(),
            },
            "my_mfa": {
                "enabled": bool(getattr(request.user, "privileged_mfa", None)
                                and request.user.privileged_mfa.confirmed_at),
                "remaining_recovery_codes": remaining,
            },
            "my_sessions": [_own(item, request.auth.pk) for item in owner_sessions],
            "trend": {
                "granularity": grain,
                "labels": [date.isoformat() for date in dates],
                "successes": [observed.get(date, {}).get("successful", 0) for date in dates],
                "failures": [observed.get(date, {}).get("failed", 0) for date in dates],
            },
            "sources": {
                "sessions": "EstablishmentWebSession · sessions non révoquées, non expirées et non inactives",
                "mfa": "PrivilegedMFADevice.confirmed_at",
                "attempts": "LoginAttempt · tentatives enregistrées, sans exhaustivité garantie",
            },
        })


class SuperadminRevokeOwnSessionE62(_SecurityBase):
    """POST: carefully revoke only another personal web session, never the current one."""

    @transaction.atomic
    def post(self, request, session_id):
        if request.data.get("confirmation") != "REVOQUER":
            return error_response("Confirmation explicite requise.", status_code=400)
        row = get_object_or_404(
            EstablishmentWebSession.objects.select_for_update(),
            pk=session_id, user=request.user,
        )
        if row.pk == request.auth.pk:
            return error_response(
                "La session utilisée ne peut pas être révoquée depuis cette page.",
                status_code=409,
            )
        now = timezone.now()
        if (row.revoked_at is not None or row.expires_at <= now
                or row.last_seen_at <= now - timedelta(
                    minutes=settings.ESTABLISHMENT_WEB_SESSION_IDLE_MINUTES,
                )):
            return error_response("Session déjà fermée ou expirée.", status_code=409)
        row.revoked_at = now
        row.save(update_fields=["revoked_at"])
        log_audit_event(
            "sessions_revoked", user=request.user, request=request,
            metadata={
                "channel": "web",
                "session_id": row.pk,
                "source": "superadmin_sessions_e62",
            },
        )
        return self.ok("L'autre appareil a été déconnecté.", {
            "revoked_session_id": row.pk,
        })
