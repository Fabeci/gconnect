"""E35 · Sensitive user operations isolated to MFA-verified Superadmin WebToken.

Account status and security sessions are managed here; role elevation,
unscreened account activation and deletion are deliberately not supported.
All decisions are attributable and auditable.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.models import AuditLogEntry
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import success_response, error_response
from apps.api.v1.users.models import User, EstablishmentWebSession
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


_ACTION_NAMES = {
    "ban": ("user_banned", "Compte bloqué. Les sessions ont été révoquées."),
    "unban": ("user_unbanned", "Compte débloqué. L’activation initiale reste inchangée."),
    "revoke_sessions": ("sessions_revoked", "Sessions révoquées."),
}
_AUDIT_ACTIONS = tuple(value[0] for value in _ACTION_NAMES.values())


def _eligible(target, actor):
    """Immutable privilege boundaries. Users cannot modify Superadmin accounts."""
    if target.pk == actor.pk or target.role == "superAdmin":
        return []
    actions = ["unban"] if target.is_banned else ["ban"]
    if not target.is_banned:
        actions.append("revoke_sessions")
    return actions


def _security_payload(target, actor):
    now = timezone.now()
    events = AuditLogEntry.objects.filter(
        action__in=_AUDIT_ACTIONS,
        metadata__target_user_id=target.pk,
    ).select_related("user").order_by("-created_at", "-pk")[:12]
    return {
        "id": target.pk,
        "role": target.role,
        "is_active": bool(target.is_active),
        "is_banned": bool(target.is_banned),
        "banned_reason": target.banned_reason if target.is_banned else "",
        "banned_at": target.banned_at.isoformat() if target.banned_at else None,
        "live_web_sessions": EstablishmentWebSession.objects.filter(
            user=target, revoked_at__isnull=True, expires_at__gt=now,
        ).count(),
        "eligible_actions": _eligible(target, actor),
        "history": [
            {
                "id": event.pk,
                "action": event.action,
                "label": event.get_action_display(),
                "created_at": event.created_at.isoformat(),
                "actor": (
                    event.user.get_full_name().strip() or event.user.username
                ) if event.user_id and event.user else "Compte supprimé",
                "reason": str(event.metadata.get("reason") or "")[:255],
            }
            for event in events
        ],
    }


class SuperadminUserSecurityE35(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        response = success_response("État de sécurité du compte.", _security_payload(target, request.user))
        response["Cache-Control"] = "no-store"
        return response

    @transaction.atomic
    def post(self, request, pk):
        target = get_object_or_404(User.objects.select_for_update(), pk=pk)
        action = request.data.get("action")
        reason = request.data.get("reason")
        if not isinstance(action, str) or action not in _ACTION_NAMES:
            return error_response("Action de sécurité invalide.", status_code=400)
        if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 255:
            return error_response(
                "Motif obligatoire (10 à 255 caractères).", status_code=400,
            )
        reason = reason.strip()

        if target.role == "superAdmin" or target.pk == request.user.pk:
            return error_response("Opération interdite sur un compte Superadmin.", status_code=403)
        if action == "ban" and target.is_banned:
            return error_response("Compte déjà bloqué.", status_code=409)
        if action == "unban" and not target.is_banned:
            return error_response("Compte non bloqué.", status_code=409)
        if action == "revoke_sessions" and target.is_banned:
            return error_response("Compte bloqué. Aucun nouvel accès autorisé.", status_code=409)

        now = timezone.now()
        sessions_revoked = 0
        mobile_token_revoked = 0
        if action == "ban":
            target.is_banned = True
            target.banned_reason = reason
            target.banned_at = now
            target.save(update_fields=["is_banned", "banned_reason", "banned_at"])
        elif action == "unban":
            target.is_banned = False
            target.banned_reason = ""
            target.banned_at = None
            target.save(update_fields=["is_banned", "banned_reason", "banned_at"])

        if action in ("ban", "revoke_sessions"):
            sessions_revoked = EstablishmentWebSession.objects.filter(
                user=target, revoked_at__isnull=True,
            ).update(revoked_at=now)
            mobile_tokens = Token.objects.filter(user=target)
            mobile_token_revoked = mobile_tokens.count()
            mobile_tokens.delete()

        audit_action, message = _ACTION_NAMES[action]
        log_audit_event(
            audit_action, user=request.user, request=request,
            metadata={
                "target_user_id": target.pk,
                "reason": reason,
                "source": "superadmin_user_directory_e35",
                "web_sessions_revoked": sessions_revoked,
                "mobile_tokens_revoked": mobile_token_revoked,
            },
        )
        response = success_response(message, {
            "action": action,
            "user_id": target.pk,
            "web_sessions_revoked": sessions_revoked,
            "mobile_tokens_revoked": mobile_token_revoked,
            "security": _security_payload(target, request.user),
        })
        response["Cache-Control"] = "no-store"
        return response
