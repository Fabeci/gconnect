"""Opt-in device-scoped login for G-Connect institution and platform web consoles."""
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.users.models import (
    EstablishmentWebSession, LoginAttempt, PrivilegedAuthChallenge, User,
)
from apps.api.v1.users.throttles import LoginThrottle
from .enterprise_access import enterprise_access
from .views import LOGIN_LOCKOUT_THRESHOLD, LOGIN_LOCKOUT_WINDOW_MINUTES, _client_ip
from .web_authentication import (
    EstablishmentWebTokenAuthentication, WEB_SESSION_COOKIE_NAME, ROLE_COOKIE_NAMES,
    clear_web_session_cookie,
)
from .privileged_security import issue_challenge, token_digest
from .email_mfa import email_mfa_for_user, send_email_code, EmailMFADeliveryError


class EstablishmentWebLoginView(APIView):
    """POST /users/web-login/ — never creates or returns the mobile token."""
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        email = str(request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        if not email or not password:
            return error_response("Email et mot de passe requis.", status_code=400)

        ip = _client_ip(request)
        cutoff = timezone.now() - timedelta(minutes=LOGIN_LOCKOUT_WINDOW_MINUTES)
        failures = LoginAttempt.objects.filter(
            email__iexact=email, success=False, created_at__gte=cutoff,
        ).count()
        if failures >= LOGIN_LOCKOUT_THRESHOLD:
            return error_response("Trop de tentatives. Réessayez plus tard.", status_code=429)

        try:
            user = User.objects.get(email__iexact=email)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            LoginAttempt.objects.create(email=email, ip_address=ip, success=False)
            log_audit_event("login_failed", request=request, metadata={"channel": "web"})
            return error_response("Identifiants incorrects.", status_code=401)

        if not user.check_password(password):
            LoginAttempt.objects.create(email=email, ip_address=ip, success=False)
            log_audit_event("login_failed", user=user, request=request, metadata={"channel": "web"})
            return error_response("Identifiants incorrects.", status_code=401)

        if not user.is_active or user.is_banned or user.role not in ("etablissement", "superAdmin", "enterprise"):
            return error_response("Ce compte n'est pas autorisé à accéder à cet espace.", status_code=403)
        if user.role == "etablissement":
            admin = getattr(user, "institution_admin_profile", None)
            if not admin or not admin.institution.is_active:
                return error_response("Établissement indisponible.", status_code=403)

        if user.role == "enterprise" and enterprise_access(user)[0] is None:
            return error_response("Profil Entreprise indisponible.", status_code=403)

        device = getattr(user, "privileged_mfa", None)
        if device and device.locked_until:
            if timezone.now() < device.locked_until:
                return error_response("Double authentification temporairement bloquée. Réessayez plus tard.", status_code=429)
            device.failed_attempts = 0
            device.locked_until = None
            device.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
        needs_enrollment = device is None or device.confirmed_at is None
        email_method = email_mfa_for_user(user)
        # Do not commit an unusable challenge when the provider rejects delivery.
        # Existing TOTP remains the default until HTTPS email is configured.
        with transaction.atomic():
            challenge_token = issue_challenge(user, enroll=needs_enrollment and not email_method)
            if email_method:
                challenge_record = PrivilegedAuthChallenge.objects.get(
                    token_hash=token_digest(challenge_token)
                )
                try:
                    send_email_code(user, challenge_record)
                except EmailMFADeliveryError:
                    transaction.set_rollback(True)
                    return error_response(
                        "Impossible d'envoyer le code. Réessayez ultérieurement.",
                        status_code=503,
                    )
            LoginAttempt.objects.create(email=email, ip_address=ip, success=True)
        log_audit_event("mfa_challenge_issued", user=user, request=request, metadata={
            "channel": "web", "method": "email" if email_method else "totp"
        })
        return success_response("Mot de passe vérifié. Double authentification requise.", {
            "challenge": challenge_token, "mfa_required": True,
            "mfa_action": "verify" if email_method else ("enroll" if needs_enrollment else "verify"),
            "mfa_method": "email" if email_method else "totp",
            "challenge_expires_in": 300, "email": user.email,
        })


def _trusted_web_origin(request):
    """A resume endpoint must not expose a bearer secret to unrelated sites."""
    origin = request.headers.get("Origin", "").rstrip("/")
    if not origin or origin == "null":
        return False
    allowed = set(getattr(settings, "CORS_ALLOWED_ORIGINS", ()))
    own = request.build_absolute_uri("/")
    own_parts = urlsplit(own)
    allowed.add(f"{own_parts.scheme}://{own_parts.netloc}")
    app_url = getattr(settings, "GCONNECT_WEB_APP_URL", "")
    if app_url:
        app_parts = urlsplit(app_url)
        allowed.add(f"{app_parts.scheme}://{app_parts.netloc}")
    return origin in allowed


class EstablishmentWebResumeView(APIView):
    """POST /users/web-resume/ — restore one *already MFA-verified* live device."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not _trusted_web_origin(request):
            return error_response("Origine de reprise de session non autorisée.", status_code=403)
        requested_role = str(request.data.get("role") or "").strip()
        if requested_role and requested_role not in ROLE_COOKIE_NAMES:
            return error_response("Espace professionnel inconnu.", status_code=400)
        # Scoped cookie first. Legacy clients may still resume their original
        # session, but a mismatched role must never be accepted.
        scoped_raw = request.COOKIES.get(ROLE_COOKIE_NAMES[requested_role]) if requested_role else None
        raw = scoped_raw or request.COOKIES.get(WEB_SESSION_COOKIE_NAME)
        if not raw:
            return error_response("Aucune session web active.", status_code=401)
        try:
            user, session = EstablishmentWebTokenAuthentication.authenticate_raw(raw)
        except AuthenticationFailed:
            return clear_web_session_cookie(
                error_response("Session expirée ou révoquée. Reconnectez-vous.", status_code=401),
                requested_role if scoped_raw else None,
            )
        if requested_role and user.role != requested_role:
            return error_response("Session associée à un autre espace.", status_code=401)
        response = success_response("Session web active.", {
            "token": raw, "token_type": "WebToken",
            "role": user.role, "expires_at": session.expires_at.isoformat(),
        })
        response["Cache-Control"] = "no-store"
        return response


class WebSessionOnlyView(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


class EstablishmentWebLogoutView(WebSessionOnlyView):
    """POST /users/web-logout/ — revokes only this web device."""

    def post(self, request):
        request.auth.revoke()
        log_audit_event("logout", user=request.user, request=request, metadata={"channel": "web"})
        return clear_web_session_cookie(success_response("Session web fermée."), request.user.role)


class EstablishmentWebSessionsView(WebSessionOnlyView):
    """GET /users/web-sessions/ — recent active browser sessions, no secrets."""

    def get(self, request):
        now = timezone.now()
        idle_cutoff = now - timedelta(minutes=settings.ESTABLISHMENT_WEB_SESSION_IDLE_MINUTES)
        sessions = EstablishmentWebSession.objects.filter(
            user=request.user, revoked_at__isnull=True,
            expires_at__gt=now, last_seen_at__gt=idle_cutoff,
        ).order_by("-created_at", "-id")[:20]
        data = [{
            "id": s.pk,
            "current": s.pk == request.auth.pk,
            "created_at": s.created_at.isoformat(),
            "last_seen_at": s.last_seen_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "user_agent": s.user_agent,
        } for s in sessions]
        return success_response("Appareils connectés.", data)


class EstablishmentWebRevokeSessionView(WebSessionOnlyView):
    """POST /users/web-sessions/<id>/revoke/ — owners may revoke a device."""

    def post(self, request, session_id):
        session = get_object_or_404(
            EstablishmentWebSession, pk=session_id, user=request.user,
        )
        session.revoke()
        log_audit_event("sessions_revoked", user=request.user, request=request,
                        metadata={"channel": "web", "session_id": session_id})
        return success_response("Appareil déconnecté.")
