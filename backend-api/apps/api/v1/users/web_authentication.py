"""Privileged web bearer authentication; DRF mobile Token remains supported."""
import hashlib
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .enterprise_access import enterprise_access
from .models import EstablishmentWebSession

_ACTIVITY_WRITE_INTERVAL = timedelta(minutes=5)

WEB_SESSION_COOKIE_NAME = "gconnect_web_session"
ROLE_COOKIE_NAMES = {
    "superAdmin": "gconnect_web_session_superadmin",
    "etablissement": "gconnect_web_session_etablissement",
    "enterprise": "gconnect_web_session_entreprise",
}
# A dedicated path keeps the cookie away from mobile and backoffice API routes.
WEB_SESSION_COOKIE_PATH = "/api/v1/users/"


def set_web_session_cookie(response, raw, request, expires_at, role):
    """Save the MFA-verified device credential outside JavaScript storage."""
    max_age = max(1, int((expires_at - timezone.now()).total_seconds()))
    cookie_options = dict(
        max_age=max_age, path=WEB_SESSION_COOKIE_PATH,
        secure=not settings.DEBUG or request.is_secure(),
        httponly=True, samesite="Lax",
    )
    # Legacy cookie stays available to older clients. The portal-specific
    # cookie is never overwritten by a login to another professional role.
    response.set_cookie(WEB_SESSION_COOKIE_NAME, raw, **cookie_options)
    response.set_cookie(ROLE_COOKIE_NAMES[role], raw, **cookie_options)
    response["Cache-Control"] = "no-store"
    return response


def clear_web_session_cookie(response, role=None):
    response.delete_cookie(
        WEB_SESSION_COOKIE_NAME,
        path=WEB_SESSION_COOKIE_PATH,
        samesite="Lax",
    )
    if role in ROLE_COOKIE_NAMES:
        response.delete_cookie(ROLE_COOKIE_NAMES[role], path=WEB_SESSION_COOKIE_PATH, samesite="Lax")
    response["Cache-Control"] = "no-store"
    return response



class EstablishmentWebTokenAuthentication(BaseAuthentication):
    """Accept `Authorization: WebToken <secret>` with a hashed, revocable session."""

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != b"webtoken":
            return None
        if len(header) != 2:
            raise AuthenticationFailed("Identifiant de session invalide.")
        try:
            raw = header[1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Identifiant de session invalide.") from exc
        return self.authenticate_raw(raw)

    @staticmethod
    def authenticate_raw(raw):
        """Validate the same revocable credential from an HTTP-only browser cookie."""
        if not isinstance(raw, str) or not 40 <= len(raw) <= 128 or not raw.isascii():
            raise AuthenticationFailed("Identifiant de session invalide.")

        digest = hashlib.sha256(raw.encode("ascii")).hexdigest()
        session = EstablishmentWebSession.objects.select_related("user").filter(
            token_hash=digest,
        ).first()
        if session is None:
            raise AuthenticationFailed("Session inconnue. Reconnectez-vous.")

        now = timezone.now()
        idle = timedelta(minutes=settings.ESTABLISHMENT_WEB_SESSION_IDLE_MINUTES)
        if session.revoked_at or now >= session.expires_at or now - session.last_seen_at >= idle:
            session.revoke()
            raise AuthenticationFailed("Session expirée ou révoquée. Reconnectez-vous.")

        user = session.user
        if not user.is_active or user.is_banned or user.role not in ("etablissement", "superAdmin", "enterprise"):
            session.revoke()
            raise AuthenticationFailed("Compte non autorisé.")
        if user.role == "etablissement":
            admin = getattr(user, "institution_admin_profile", None)
            if not admin or not admin.institution.is_active:
                session.revoke()
                raise AuthenticationFailed("Établissement indisponible.")
        if user.role == "enterprise" and enterprise_access(user)[0] is None:
            session.revoke()
            raise AuthenticationFailed("Entreprise indisponible.")
        mfa = getattr(user, "privileged_mfa", None)
        if not mfa or mfa.confirmed_at is None:
            session.revoke()
            raise AuthenticationFailed("Double authentification nécessaire.")

        if now - session.last_seen_at >= _ACTIVITY_WRITE_INTERVAL:
            session.last_seen_at = now
            session.save(update_fields=["last_seen_at"])
        return user, session

    def authenticate_header(self, request):
        return "WebToken"
