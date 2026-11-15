# audit.py
"""Point d'entrée unique pour journaliser une action sensible."""
from apps.api.v1.core.models import AuditLogEntry


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit_event(action, *, user=None, request=None, metadata=None):
    AuditLogEntry.objects.create(
        user=user,
        action=action,
        ip_address=_client_ip(request),
        metadata=metadata or {},
    )
