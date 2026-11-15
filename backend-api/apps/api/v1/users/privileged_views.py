"""E4 enterprise invitation and TOTP step-up endpoints (web-only privileges)."""
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.establishments.models import Institution
from .enterprise_access import enterprise_access
from .email_mfa import email_mfa_enabled, verify_email_code, send_email_code, EmailMFADeliveryError
from .models import (
    EstablishmentInvitation, EstablishmentWebSession, InstitutionAdmin, LoginSession,
    PrivilegedAuthChallenge, PrivilegedMFADevice, User,
)
from .privileged_security import (
    MAX_CHALLENGE_FAILURES, consume_recovery_code, encrypt_totp,
    generate_recovery_codes, generate_totp_secret, provisioning_uri,
    token_digest, verify_totp, issue_challenge,
)
from .throttles import OtpThrottle, OtpResendThrottle, RegistrationThrottle
from .web_authentication import EstablishmentWebTokenAuthentication, set_web_session_cookie

INVITATION_LIFETIME = timedelta(hours=48)
MFA_SETUP_LIFETIME = timedelta(minutes=10)
PRIVILEGED_ROLES = ("etablissement", "superAdmin", "enterprise")


def _digest_or_none(raw):
    if not isinstance(raw, str) or not 30 <= len(raw) <= 128 or not raw.isascii():
        return None
    return token_digest(raw)


def _privileged_enabled(user):
    if not user.is_active or user.is_banned or user.role not in PRIVILEGED_ROLES:
        return False
    if user.role == "etablissement":
        profile = getattr(user, "institution_admin_profile", None)
        return bool(profile and profile.institution.is_active)
    if user.role == "enterprise":
        return enterprise_access(user)[0] is not None
    return True


class _SuperadminView(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _allowed(self, request):
        return request.user.role == "superAdmin" and request.user.is_active and not request.user.is_banned


class EstablishmentInvitationsView(_SuperadminView):
    """Superadmin only: invite a school administrator and list invitations."""

    def get(self, request):
        if not self._allowed(request):
            return error_response("Accès réservé au Superadmin.", status_code=403)
        invites = EstablishmentInvitation.objects.select_related("institution").order_by("-created_at")[:50]
        return success_response("Invitations.", [{
            "id": inv.pk, "email": inv.email,
            "institution_id": inv.institution_id, "institution_name": inv.institution.name,
            "created_at": inv.created_at.isoformat(), "expires_at": inv.expires_at.isoformat(),
            "accepted": inv.accepted_at is not None, "revoked": inv.revoked_at is not None,
        } for inv in invites])

    def post(self, request):
        if not self._allowed(request):
            return error_response("Accès réservé au Superadmin.", status_code=403)
        email = str(request.data.get("email") or "").strip().lower()
        institution_id = request.data.get("institution_id")
        try:
            validate_email(email)
        except ValidationError:
            return error_response("Adresse e-mail invalide.", status_code=400)
        institution = Institution.objects.filter(pk=institution_id, is_active=True).first() if str(institution_id or "").isdigit() else None
        if not institution:
            return error_response("Établissement inexistant ou inactif.", status_code=400)
        if User.objects.filter(email__iexact=email).exists():
            return error_response("Un compte existe déjà pour cette adresse.", status_code=409)

        public_url = getattr(settings, "GCONNECT_WEB_APP_URL", "") or (
            "http://127.0.0.1:8086" if settings.DEBUG else ""
        )
        if not public_url or (not settings.DEBUG and not public_url.startswith("https://")):
            return error_response("URL HTTPS de l'interface non configurée.", status_code=503)
        email_backend = getattr(settings, "EMAIL_BACKEND", "")
        if not settings.DEBUG and ("console" in email_backend or "dummy" in email_backend):
            return error_response("Service d'envoi d'e-mails non configuré.", status_code=503)

        raw = secrets.token_urlsafe(48)
        now = timezone.now()
        link = public_url.rstrip("/") + "/etablissement-activation.html#invitation=" + raw
        with transaction.atomic():
            EstablishmentInvitation.objects.select_for_update().filter(
                email__iexact=email, accepted_at__isnull=True, revoked_at__isnull=True,
            ).update(revoked_at=now)
            invite = EstablishmentInvitation.objects.create(
                email=email, institution=institution, invited_by=request.user,
                token_hash=token_digest(raw), expires_at=now + INVITATION_LIFETIME,
            )
            try:
                sent = send_mail(
                    subject="Invitation G-Connect — accès établissement",
                    message=(
                        "Bonjour,\n\nVous avez été invité(e) à administrer "
                        + institution.name + " sur G-Connect.\n\n"
                        "Pour confirmer votre adresse et définir votre mot de passe, "
                        "ouvrez ce lien dans les 48 heures :\n" + link
                        + "\n\nSi vous n'attendiez pas cette invitation, ignorez ce message."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email], fail_silently=False,
                )
            except Exception:
                sent = 0
            if sent != 1:
                # Force transaction rollback: never leave an undelivered active invite.
                transaction.set_rollback(True)
                return error_response("Invitation non envoyée. Vérifiez le serveur e-mail.", status_code=503)
        log_audit_event("invitation_sent", user=request.user, request=request,
                        metadata={"invitation_id": invite.pk, "institution_id": institution.pk})
        return success_response("Invitation envoyée.", {"id": invite.pk, "expires_at": invite.expires_at.isoformat()})


class EstablishmentInvitationRevokeView(_SuperadminView):
    def post(self, request, invitation_id):
        if not self._allowed(request):
            return error_response("Accès réservé au Superadmin.", status_code=403)
        changed = EstablishmentInvitation.objects.filter(
            pk=invitation_id, accepted_at__isnull=True, revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        if not changed:
            return error_response("Invitation inconnue ou déjà clôturée.", status_code=404)
        log_audit_event("invitation_revoked", user=request.user, request=request,
                        metadata={"invitation_id": invitation_id})
        return success_response("Invitation révoquée.")


class EstablishmentInvitationPreviewView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        digest = _digest_or_none(request.data.get("invitation"))
        now = timezone.now()
        invite = EstablishmentInvitation.objects.select_related("institution").filter(
            token_hash=digest, accepted_at__isnull=True, revoked_at__isnull=True, expires_at__gt=now,
            institution__is_active=True,
        ).first() if digest else None
        if not invite:
            return error_response("Invitation invalide ou expirée.", status_code=400)
        return success_response("Invitation valide.", {
            "email": invite.email, "institution": invite.institution.name,
            "expires_at": invite.expires_at.isoformat(),
        })


class EstablishmentInvitationAcceptView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [RegistrationThrottle]

    @transaction.atomic
    def post(self, request):
        digest = _digest_or_none(request.data.get("invitation"))
        password = request.data.get("password")
        if not digest or not isinstance(password, str):
            return error_response("Invitation et mot de passe requis.", status_code=400)
        invite = EstablishmentInvitation.objects.select_for_update().select_related("institution").filter(
            token_hash=digest, accepted_at__isnull=True, revoked_at__isnull=True,
            expires_at__gt=timezone.now(), institution__is_active=True,
        ).first()
        if not invite:
            return error_response("Invitation invalide ou expirée.", status_code=400)
        if User.objects.filter(email__iexact=invite.email).exists():
            return error_response("Cette adresse possède déjà un compte.", status_code=409)
        user = User(
            username="school_" + uuid.uuid4().hex,
            email=invite.email, role="etablissement", is_active=True,
            first_name=str(request.data.get("first_name") or "").strip()[:150],
            last_name=str(request.data.get("last_name") or "").strip()[:150],
        )
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            return error_response(" ".join(exc.messages), status_code=400)
        user.set_password(password)
        user.save()
        InstitutionAdmin.objects.create(user=user, institution=invite.institution)
        invite.accepted_user = user
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["accepted_user", "accepted_at"])
        log_audit_event("invitation_accepted", user=user, request=request,
                        metadata={"invitation_id": invite.pk, "institution_id": invite.institution_id})
        return success_response("Adresse confirmée. Connectez-vous pour activer votre double authentification.", {
            "email": user.email,
        })


def _locked_challenge(request):
    digest = _digest_or_none(request.data.get("challenge"))
    if not digest:
        return None
    now = timezone.now()
    challenge = PrivilegedAuthChallenge.objects.select_for_update().select_related("user").filter(
        token_hash=digest, consumed_at__isnull=True, expires_at__gt=now,
        attempts__lt=MAX_CHALLENGE_FAILURES,
    ).first()
    if not challenge or not _privileged_enabled(challenge.user):
        return None
    return challenge


class PrivilegedMFASetupView(APIView):
    """An unverified pre-auth challenge may enroll TOTP; never access dashboard."""
    authentication_classes = []
    permission_classes = []
    throttle_classes = [OtpThrottle]

    @transaction.atomic
    def post(self, request):
        challenge = _locked_challenge(request)
        if not challenge:
            return error_response("Connexion expirée. Recommencez.", status_code=401)
        if challenge.kind != PrivilegedAuthChallenge.KIND_ENROLL:
            return error_response("Authentification déjà configurée.", status_code=409)
        device, _ = PrivilegedMFADevice.objects.select_for_update().get_or_create(user=challenge.user)
        if device.confirmed_at is not None:
            return error_response("Authentification déjà activée.", status_code=409)
        raw = generate_totp_secret()
        device.encrypted_secret = encrypt_totp(raw)
        device.setup_expires_at = timezone.now() + MFA_SETUP_LIFETIME
        device.last_used_step = -1
        device.save(update_fields=["encrypted_secret", "setup_expires_at", "last_used_step", "updated_at"])
        return success_response("Scannez ce code dans votre application d'authentification.", {
            "secret": raw, "otpauth_uri": provisioning_uri(challenge.user, raw),
            "expires_at": device.setup_expires_at.isoformat(),
        })


class PrivilegedEmailResendView(APIView):
    """Reissue a short-lived OTP only for an existing password-verified challenge."""
    authentication_classes = []
    permission_classes = []
    throttle_classes = [OtpResendThrottle]

    @transaction.atomic
    def post(self, request):
        if not email_mfa_enabled():
            return error_response("Envoi e-mail indisponible.", status_code=503)
        challenge = _locked_challenge(request)
        if not challenge or challenge.kind != PrivilegedAuthChallenge.KIND_VERIFY:
            return error_response("Connexion expirée. Recommencez.", status_code=401)
        now = timezone.now()
        if now - challenge.created_at < timedelta(seconds=60):
            return error_response("Un code vient d'être envoyé. Réessayez dans une minute.", status_code=429)
        recent = PrivilegedAuthChallenge.objects.filter(
            user=challenge.user, created_at__gte=now - timedelta(minutes=15),
        ).count()
        if recent >= 5:
            return error_response("Trop de demandes. Réessayez plus tard.", status_code=429)

        user = challenge.user
        replacement_token = issue_challenge(user, enroll=False)
        replacement = PrivilegedAuthChallenge.objects.get(
            token_hash=token_digest(replacement_token)
        )
        try:
            send_email_code(user, replacement)
        except EmailMFADeliveryError:
            transaction.set_rollback(True)
            return error_response("Impossible d'envoyer le code.", status_code=503)
        log_audit_event("mfa_challenge_issued", user=user, request=request,
                        metadata={"channel": "web", "method": "email_resend"})
        return success_response("Un nouveau code a été envoyé.", {
            "challenge": replacement_token, "challenge_expires_in": 300,
        })


class PrivilegedMFAVerifyView(APIView):
    """Complete MFA atomically; only then issue a revocable WebToken."""
    authentication_classes = []
    permission_classes = []
    throttle_classes = [OtpThrottle]

    @transaction.atomic
    def post(self, request):
        challenge = _locked_challenge(request)
        if not challenge:
            return error_response("Connexion expirée ou bloquée. Recommencez.", status_code=401)
        code = str(request.data.get("code") or "").strip()
        if not code:
            return error_response("Code d'authentification requis.", status_code=400)
        user = challenge.user
        device = PrivilegedMFADevice.objects.select_for_update().filter(user=user).first()
        now = timezone.now()
        first_enrollment = challenge.kind == PrivilegedAuthChallenge.KIND_ENROLL
        emailed = verify_email_code(challenge, code)
        if not emailed and not email_mfa_enabled() and (
            not device or
            (first_enrollment and device.confirmed_at is not None) or
            (not first_enrollment and device.confirmed_at is None)
        ):
            return error_response("Configuration MFA indisponible. Recommencez.", status_code=409)
        if device and device.locked_until and now < device.locked_until:
            return error_response("Double authentification temporairement bloquée.", status_code=429)
        if first_enrollment and (not device.setup_expires_at or now >= device.setup_expires_at):
            return error_response("Configuration expirée. Recommencez.", status_code=400)

        accepted_step = (
            None if emailed or device is None or device.confirmed_at is None
            else verify_totp(device, code)
        )
        recovered = False
        if not emailed and accepted_step is None and not first_enrollment and device:
            recovered = consume_recovery_code(user, code)
        if not emailed and accepted_step is None and not recovered:
            challenge.attempts += 1
            if device:
                device.failed_attempts += 1
                if device.failed_attempts >= MAX_CHALLENGE_FAILURES:
                    device.locked_until = now + timedelta(minutes=15)
            if challenge.attempts >= MAX_CHALLENGE_FAILURES:
                challenge.consumed_at = now
            challenge.save(update_fields=["attempts", "consumed_at"])
            if device:
                device.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
            return error_response("Code incorrect ou déjà utilisé.", status_code=401)

        recovery_codes = None
        if device:
            device.failed_attempts = 0
            device.locked_until = None
            if accepted_step is not None:
                device.last_used_step = accepted_step
            if first_enrollment:
                device.confirmed_at = now
                device.setup_expires_at = None
                recovery_codes = generate_recovery_codes(user)
                EstablishmentWebSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=now)
            device.save(update_fields=(
                ["confirmed_at", "setup_expires_at", "last_used_step", "failed_attempts", "locked_until", "updated_at"]
                if first_enrollment else ["last_used_step", "failed_attempts", "locked_until", "updated_at"]
            ))
        challenge.consumed_at = now
        challenge.save(update_fields=["consumed_at"])
        session, credential = EstablishmentWebSession.issue(user, request)
        LoginSession.objects.create(
            user=user, ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
        log_audit_event("mfa_success", user=user, request=request,
                        metadata={"recovery_used": recovered, "enrolled": first_enrollment, "method": "email" if emailed else "totp"})
        payload = {
            "token": credential, "token_type": "WebToken",
            "expires_at": session.expires_at.isoformat(), "user_id": user.pk,
            "email": user.email, "role": user.role,
        }
        if recovery_codes is not None:
            payload["recovery_codes"] = recovery_codes
        response = success_response("Connexion sécurisée réussie.", payload)
        return set_web_session_cookie(response, credential, request, session.expires_at, user.role)
