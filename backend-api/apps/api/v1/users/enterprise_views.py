"""E5.3 — Enterprise invitations, activation, access and recruiter management."""
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from .enterprise_access import enterprise_access
from .models import (
    Enterprise, EnterpriseInvitation, EnterpriseMember, EstablishmentWebSession, User,
)
from .privileged_security import token_digest
from .throttles import RegistrationThrottle, OtpThrottle
from .web_authentication import EstablishmentWebTokenAuthentication

INVITATION_LIFETIME = timedelta(hours=48)


def _invitation_digest(raw):
    if not isinstance(raw, str) or not 30 <= len(raw) <= 128 or not raw.isascii():
        return None
    return token_digest(raw)


def _email(value):
    email = str(value or "").strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return None
    return email


def _mail_is_ready():
    url = getattr(settings, "GCONNECT_WEB_APP_URL", "") or (
        "http://127.0.0.1:8086" if settings.DEBUG else ""
    )
    backend = str(getattr(settings, "EMAIL_BACKEND", "")).lower()
    if not url or (not settings.DEBUG and not url.startswith("https://")):
        return None
    # Fake mail backends report success but never deliver a real invitation.
    if not settings.DEBUG and any(kind in backend for kind in
                              ("console", "dummy", "locmem", "filebased")):
        return None
    return url


def _send_invite(request, *, email, kind, company_name, sector="", company=None):
    if User.objects.filter(email__iexact=email).exists():
        return error_response("Un compte existe déjà pour cette adresse.", status_code=409)
    url = _mail_is_ready()
    if not url:
        return error_response("URL HTTPS ou service e-mail non configuré.", status_code=503)
    raw = secrets.token_urlsafe(48)
    now = timezone.now()
    invite_link = url.rstrip("/") + "/entreprise-activation.html#invitation=" + raw
    with transaction.atomic():
        EnterpriseInvitation.objects.select_for_update().filter(
            email__iexact=email, kind=kind, enterprise=company,
            accepted_at__isnull=True, revoked_at__isnull=True,
        ).update(revoked_at=now)
        invite = EnterpriseInvitation.objects.create(
            email=email, kind=kind, company_name=company_name,
            sector=sector, enterprise=company, invited_by=request.user,
            token_hash=token_digest(raw), expires_at=now + INVITATION_LIFETIME,
        )
        try:
            sent = send_mail(
                subject="G-Connect — invitation professionnelle",
                message=(
                    "Bonjour,\n\nVous avez été invité(e) sur G-Connect en tant que "
                    + ("responsable" if kind == EnterpriseInvitation.KIND_OWNER else "recruteur")
                    + " pour " + company_name + ".\n\n"
                    + "Confirmez votre adresse et créez votre mot de passe en ouvrant "
                    + "ce lien personnel sous 48 heures :\n" + invite_link
                    + "\n\nSi vous n'attendiez pas cette invitation, ignorez ce message."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email], fail_silently=False,
            )
        except Exception:
            sent = 0
        if sent != 1:
            transaction.set_rollback(True)
            return error_response("Invitation non envoyée. Vérifiez le serveur e-mail.", status_code=503)
    log_audit_event("enterprise_invitation_sent", user=request.user, request=request,
                    metadata={"invitation_id": invite.pk, "kind": kind, "enterprise_id": company.pk if company else None})
    return success_response("Invitation envoyée.", {
        "id": invite.pk, "expires_at": invite.expires_at.isoformat(),
    })


def _invitation_list(queryset):
    return [{
        "id": invite.pk, "email": invite.email, "kind": invite.kind,
        "company_name": invite.company_name, "enterprise_id": invite.enterprise_id,
        "expires_at": invite.expires_at.isoformat(),
        "accepted": invite.accepted_at is not None, "revoked": invite.revoked_at is not None,
    } for invite in queryset.order_by("-created_at")[:50]]


class _WebOnly(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


class SuperadminEnterpriseInvitesView(_WebOnly):
    """Only a verified MFA Superadmin may invite the first company owner."""
    throttle_classes = [RegistrationThrottle]

    def _allowed(self, request):
        return request.user.role == "superAdmin" and request.user.is_active and not request.user.is_banned

    def get(self, request):
        if not self._allowed(request):
            return error_response("Accès Superadmin requis.", status_code=403)
        return success_response("Invitations entreprises.", _invitation_list(
            EnterpriseInvitation.objects.filter(kind=EnterpriseInvitation.KIND_OWNER),
        ))

    def post(self, request):
        if not self._allowed(request):
            return error_response("Accès Superadmin requis.", status_code=403)
        email = _email(request.data.get("email"))
        name = str(request.data.get("company_name") or "").strip()
        sector = str(request.data.get("sector") or "").strip()
        if not email or not name or len(name) > 255 or not sector or len(sector) > 100:
            return error_response("E-mail, entreprise et secteur valides requis.", status_code=400)
        return _send_invite(
            request, email=email, kind=EnterpriseInvitation.KIND_OWNER,
            company_name=name, sector=sector,
        )


class EnterpriseRecruiterInvitesView(_WebOnly):
    """Only the verified company owner can add recruiters to its tenant."""
    throttle_classes = [RegistrationThrottle]

    def _owner(self, request):
        company, is_owner = enterprise_access(request.user)
        return company if is_owner else None

    def get(self, request):
        company = self._owner(request)
        if company is None:
            return error_response("Accès responsable entreprise requis.", status_code=403)
        return success_response("Invitations recruteurs.", _invitation_list(
            EnterpriseInvitation.objects.filter(enterprise=company, kind=EnterpriseInvitation.KIND_RECRUITER),
        ))

    def post(self, request):
        company = self._owner(request)
        if company is None:
            return error_response("Accès responsable entreprise requis.", status_code=403)
        email = _email(request.data.get("email"))
        if not email:
            return error_response("Adresse e-mail invalide.", status_code=400)
        return _send_invite(
            request, email=email, kind=EnterpriseInvitation.KIND_RECRUITER,
            company_name=company.company_name, company=company,
        )


class EnterpriseInvitationRevokeView(_WebOnly):
    def post(self, request, invitation_id):
        company, is_owner = enterprise_access(request.user)
        if request.user.role == "superAdmin" and not request.user.is_banned:
            queryset = EnterpriseInvitation.objects.filter(kind=EnterpriseInvitation.KIND_OWNER)
        elif company and is_owner:
            queryset = EnterpriseInvitation.objects.filter(
                enterprise=company, kind=EnterpriseInvitation.KIND_RECRUITER,
            )
        else:
            return error_response("Accès refusé.", status_code=403)
        changed = queryset.filter(
            pk=invitation_id, accepted_at__isnull=True, revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        if not changed:
            return error_response("Invitation inconnue ou déjà clôturée.", status_code=404)
        log_audit_event("enterprise_invitation_revoked", user=request.user, request=request,
                        metadata={"invitation_id": invitation_id})
        return success_response("Invitation révoquée.")


class EnterpriseInvitationPreviewView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        digest = _invitation_digest(request.data.get("invitation"))
        invite = EnterpriseInvitation.objects.select_related("enterprise").filter(
            token_hash=digest, accepted_at__isnull=True, revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).first() if digest else None
        if not invite or (invite.kind == EnterpriseInvitation.KIND_RECRUITER and (
            not invite.enterprise or not invite.enterprise.is_active or invite.enterprise.verified_at is None
        )):
            return error_response("Invitation invalide ou expirée.", status_code=400)
        return success_response("Invitation valide.", {
            "email": invite.email, "company_name": invite.company_name,
            "kind": invite.kind, "expires_at": invite.expires_at.isoformat(),
        })


class EnterpriseInvitationAcceptView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [RegistrationThrottle]

    @transaction.atomic
    def post(self, request):
        digest = _invitation_digest(request.data.get("invitation"))
        password = request.data.get("password")
        if not digest or not isinstance(password, str):
            return error_response("Invitation et mot de passe requis.", status_code=400)
        invite = EnterpriseInvitation.objects.select_for_update().select_related("enterprise").filter(
            token_hash=digest, accepted_at__isnull=True, revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).first()
        if invite is None:
            return error_response("Invitation invalide ou expirée.", status_code=400)
        if User.objects.filter(email__iexact=invite.email).exists():
            return error_response("Cette adresse possède déjà un compte.", status_code=409)
        if invite.kind == EnterpriseInvitation.KIND_RECRUITER:
            company = Enterprise.objects.select_for_update().filter(
                pk=invite.enterprise_id, is_active=True, verified_at__isnull=False,
                user__is_active=True, user__is_banned=False,
            ).first()
            if company is None:
                return error_response("Cette entreprise ne peut plus accepter d'invitations.", status_code=403)
        elif invite.kind == EnterpriseInvitation.KIND_OWNER and invite.enterprise_id is None:
            company = None
        else:
            return error_response("Type d'invitation invalide.", status_code=400)
        user = User(
            username="business_" + uuid.uuid4().hex, email=invite.email, role="enterprise",
            is_active=True, first_name=str(request.data.get("first_name") or "").strip()[:150],
            last_name=str(request.data.get("last_name") or "").strip()[:150],
        )
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            return error_response(" ".join(exc.messages), status_code=400)
        user.set_password(password)
        user.save()
        if company is None:
            company = Enterprise.objects.create(
                user=user, company_name=invite.company_name, sector=invite.sector,
                is_active=True, verified_at=timezone.now(),
            )
        else:
            EnterpriseMember.objects.create(user=user, enterprise=company)
        invite.accepted_user = user
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["accepted_user", "accepted_at"])
        log_audit_event("enterprise_invitation_accepted", user=user, request=request,
                        metadata={"invitation_id": invite.pk, "enterprise_id": company.pk})
        return success_response(
            "Adresse confirmée. Connectez-vous pour configurer votre double authentification.",
            {"email": user.email},
        )


class EnterpriseDashboardView(_WebOnly):
    """Read-only tenant summary; no applicant data from another company."""
    def get(self, request):
        company, is_owner = enterprise_access(request.user)
        if company is None:
            return error_response("Accès Entreprise vérifiée requis.", status_code=403)
        from apps.api.v1.posts.models import Application
        offers = _company_offers(company)
        count = offers.count()
        applications = Application.objects.filter(opportunity__in=offers).count()
        return success_response("Tableau de bord Entreprise.", {
            "company": {"id": company.pk, "name": company.company_name, "sector": company.sector},
            "membership": "owner" if is_owner else "recruiter",
            "stats": {"opportunities": count, "applications": applications},
        })


class EnterpriseRecruitersView(_WebOnly):
    def get(self, request):
        company, is_owner = enterprise_access(request.user)
        if not company or not is_owner:
            return error_response("Accès responsable entreprise requis.", status_code=403)
        members = EnterpriseMember.objects.filter(enterprise=company).select_related("user").order_by("-created_at")
        return success_response("Recruteurs.", [{
            "id": member.pk, "email": member.user.email,
            "name": member.user.get_full_name() or member.user.email,
            "active": member.is_active and member.user.is_active and not member.user.is_banned,
        } for member in members])


class EnterpriseRecruiterRevokeView(_WebOnly):
    @transaction.atomic
    def post(self, request, member_id):
        company, is_owner = enterprise_access(request.user)
        if not company or not is_owner:
            return error_response("Accès responsable entreprise requis.", status_code=403)
        member = EnterpriseMember.objects.select_for_update().filter(
            pk=member_id, enterprise=company, is_active=True,
        ).first()
        if member is None:
            return error_response("Recruteur inconnu ou déjà révoqué.", status_code=404)
        member.is_active = False
        member.save(update_fields=["is_active"])
        EstablishmentWebSession.objects.filter(
            user=member.user, revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        log_audit_event("enterprise_recruiter_revoked", user=request.user, request=request,
                        metadata={"member_id": member.pk, "enterprise_id": company.pk})
        return success_response("Accès recruteur révoqué.")


def _company_offers(company):
    from apps.api.v1.posts.models import Opportunity
    authors = Q(post__author=company.user) | Q(
        post__author__enterprise_membership__enterprise=company,
        post__author__enterprise_membership__is_active=True,
        post__author__is_active=True, post__author__is_banned=False,
    )
    return Opportunity.objects.filter(
        authors, enterprise=company, post__is_archived=False,
    ).select_related("post").distinct()


class EnterpriseOpportunitiesView(_WebOnly):
    """Read-only offer register. Publishing controls follow in the E5.4 sprint."""
    def get(self, request):
        company, _ = enterprise_access(request.user)
        if company is None:
            return error_response("Accès Entreprise vérifiée requis.", status_code=403)
        offers = _company_offers(company).order_by("-post__created_at")[:100]
        return success_response("Offres de votre entreprise.", [{
            "id": offer.pk, "title": offer.post.title,
            "status": offer.status, "created_at": offer.post.created_at.isoformat(),
        } for offer in offers])


class EnterpriseOfferApplicationsView(_WebOnly):
    """Only candidates of an offer actually owned by the authenticated company."""
    def get(self, request, offer_id):
        company, _ = enterprise_access(request.user)
        if company is None:
            return error_response("Accès Entreprise vérifiée requis.", status_code=403)
        offer = _company_offers(company).filter(pk=offer_id).first()
        if offer is None:
            return error_response("Offre introuvable.", status_code=404)
        applications = offer.applications.select_related("user").order_by("-created_at")[:100]
        return success_response("Candidatures reçues.", [{
            "id": app.pk, "candidate_name": app.user.get_full_name() or app.user.username,
            "status": app.status, "received_at": app.created_at.isoformat(),
        } for app in applications])
