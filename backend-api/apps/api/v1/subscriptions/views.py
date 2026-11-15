"""MFA-protected subscription catalog and manually activated billing terms."""
import calendar
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.establishments.models import Institution
from apps.api.v1.establishments.models import AlumniInstitution, StudentInstitution
from apps.api.v1.users.models import Enterprise
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication
from .models import BusinessSubscription, CommercialOffer, PriceOption, SubscriptionTopUp
from .quotas import (
    QuotaExceeded, active_institution_accounts, current_contract,
    lock_institution, quota_summary, require_available_school_seat,
)

ALLOWED_TERMS = (0, 1, 6, 12)


def _integer(value, minimum=1):
    if isinstance(value, bool) or not str(value).isdigit():
        raise ValueError("Un nombre entier est requis.")
    result = int(value)
    if result < minimum:
        raise ValueError("Nombre hors limite.")
    return result


def _money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
            raise ValueError()
        if amount >= Decimal("10000000000"):
            raise ValueError()
        return amount.quantize(Decimal("0.01"))
    except (ValueError, TypeError, InvalidOperation):
        raise ValueError("Montant non valide (deux décimales maximum).")


def _date(value):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValueError("Date ISO AAAA-MM-JJ requise.")


def _plus_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def _price_dict(p):
    return {
        "id": p.pk, "term_months": p.term_months,
        "seats": p.seats, "capacity": p.seats, "quota_unit": p.offer.quota_unit,
        "amount": str(p.amount) if p.amount is not None else None,
        "currency": p.currency, "on_quote": p.term_months == 0,
        "is_active": p.is_active,
    }


def _offer_dict(o, *, history=False):
    prices = list(o.price_options.all())
    if not history:
        prices = [p for p in prices if p.is_active]
    prices.sort(key=lambda p: (p.term_months, p.seats, p.pk))
    return {
        "id": o.pk, "slug": o.slug, "name": o.name,
        "description": o.description, "kind": o.kind,
        "quota_unit": o.quota_unit,
        "audience": o.audience, "is_active": o.is_active,
        "prices": [_price_dict(p) for p in prices],
    }


def _subscription_dict(s):
    return {
        "id": s.pk, "offer_name": s.offer_name,
        "kind": s.price_option.offer.kind,
        "institution_id": s.institution_id, "enterprise_id": s.enterprise_id,
        "organisation_name": s.institution.name if s.institution_id else s.enterprise.company_name,
        "amount": str(s.amount), "currency": s.currency,
        "seats": s.seats, "capacity": s.seats, "quota_unit": s.quota_unit,
        "quota": quota_summary(s) if s.status in ("active", "scheduled") and s.starts_at <= timezone.localdate() < s.ends_at else None,
        "starts_at": s.starts_at.isoformat(), "ends_at": s.ends_at.isoformat(),
        "status": ("expired" if s.status == "active" and s.ends_at <= timezone.localdate()
                   else "scheduled" if s.status in ("active", "scheduled") and s.starts_at > timezone.localdate()
                   else "active" if s.status == "scheduled" and s.starts_at <= timezone.localdate() < s.ends_at
                   else s.status),
    }


def _organisation_for(user):
    if user.role == "enterprise":
        ent = getattr(user, "enterprise_profile", None)
        return ("enterprise", ent) if ent is not None else (None, None)
    if user.role == "etablissement":
        admin = getattr(user, "institution_admin_profile", None)
        if admin and admin.institution.is_active:
            return "institution", admin.institution
    return None, None


class _WebOnly(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


class _SuperadminOnly(_WebOnly):
    def _guard(self, request):
        return request.user.role == "superAdmin" and request.user.is_active and not request.user.is_banned


class CatalogView(_WebOnly):
    """GET /subscriptions/catalog/ — only eligible offers, no internal audit data."""
    def get(self, request):
        role, org = _organisation_for(request.user)
        if request.user.role == "superAdmin":
            role = "all"
        elif not org:
            return error_response("Espace professionnel requis.", status_code=403)
        audiences = ("all", "institution", "enterprise") if role == "all" else ("all", role)
        offers = CommercialOffer.objects.filter(
            is_active=True, audience__in=audiences,
        ).prefetch_related("price_options").order_by("kind", "name")
        return success_response("Catalogue des abonnements.", [_offer_dict(o) for o in offers])


class MySubscriptionView(_WebOnly):
    """GET /subscriptions/my/ — server resolves its own institution or company."""
    def get(self, request):
        role, org = _organisation_for(request.user)
        if not org:
            return error_response("Espace professionnel requis.", status_code=403)
        scoped = (
            BusinessSubscription.objects.filter(enterprise=org) if role == "enterprise"
            else BusinessSubscription.objects.filter(institution=org)
        )
        # Resolve the active contract independently of the bounded history.
        # An older, still-active contract must not disappear after 30 later records.
        today = timezone.localdate()
        related = scoped.select_related("price_option__offer", "enterprise", "institution")
        current = related.filter(
            status__in=("active", "scheduled"), starts_at__lte=today, ends_at__gt=today,
        ).first()
        recent = list(related[:30])
        return success_response("Abonnement de votre organisation.", {
            "organisation_type": role, "organisation_id": org.pk,
            "current": _subscription_dict(current) if current else None,
            "quota": quota_summary(current) if current else None,
            "history": [_subscription_dict(s) for s in recent],
        })


class SuperadminOffersView(_SuperadminOnly):
    def get(self, request):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        offers = CommercialOffer.objects.prefetch_related("price_options").all()
        return success_response("Configuration des offres.", [
            _offer_dict(o, history=True) for o in offers
        ])

    def post(self, request):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        slug = str(request.data.get("slug") or "").strip().lower()
        name = str(request.data.get("name") or "").strip()
        kind = str(request.data.get("kind") or "")
        audience = str(request.data.get("audience") or "all")
        quota_unit = str(request.data.get("quota_unit") or "accounts")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,99}", slug) or not name or len(name) > 150:
            return error_response("Nom ou identifiant de l'offre invalide.")
        if (kind not in CommercialOffer.Kind.values or audience not in CommercialOffer.Audience.values
                or quota_unit not in CommercialOffer.QuotaUnit.values):
            return error_response("Modèle ou public de l'offre invalide.")
        if quota_unit == "publications" and audience != "enterprise":
            return error_response("Les offres Publications sont réservées aux entreprises.")
        if quota_unit == "accounts" and audience == "enterprise":
            return error_response("Les offres Comptes sont réservées aux établissements.")
        if audience == "enterprise" and kind != CommercialOffer.Kind.FLEXIBLE:
            return error_response("Les entreprises disposent uniquement de forfaits Publications.")
        try:
            offer = CommercialOffer.objects.create(
                slug=slug, name=name,
                description=str(request.data.get("description") or "")[:500],
                kind=kind, audience=audience, quota_unit=quota_unit, created_by=request.user,
            )
        except IntegrityError:
            return error_response("Cet identifiant d'offre existe déjà.", status_code=409)
        log_audit_event("subscription_offer_created", user=request.user, request=request, metadata={"offer_id": offer.pk})
        return success_response("Offre créée.", _offer_dict(offer), status_code=201)


class SuperadminOfferDetailView(_SuperadminOnly):
    def patch(self, request, offer_id):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        offer = get_object_or_404(CommercialOffer, pk=offer_id)
        for field in ("name", "description", "audience", "is_active"):
            if field in request.data:
                value = request.data[field]
                if field == "name" and (not isinstance(value, str) or not value.strip() or len(value) > 150):
                    return error_response("Nom d'offre invalide.")
                if field == "description" and (not isinstance(value, str) or len(value) > 500):
                    return error_response("Description invalide.")
                if field == "audience" and value not in CommercialOffer.Audience.values:
                    return error_response("Public invalide.")
                if field == "audience" and value != offer.audience:
                    # Capacity meaning must remain stable for existing prices and contracts.
                    return error_response("Le public d'une offre existante est immuable.")
                if field == "is_active" and not isinstance(value, bool):
                    return error_response("Actif doit être un booléen.")
                setattr(offer, field, value)
        offer.save()
        log_audit_event("subscription_offer_updated", user=request.user, request=request, metadata={"offer_id": offer.pk})
        return success_response("Offre mise à jour.", _offer_dict(offer))


class SuperadminPricesView(_SuperadminOnly):
    def post(self, request):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        try:
            offer_id = _integer(request.data.get("offer_id"))
            term = _integer(request.data.get("term_months"), minimum=0)
            seats = _integer(request.data.get("capacity", request.data.get("seats")))
            if term not in ALLOWED_TERMS:
                raise ValueError("Durée invalide.")
            amount = None if term == 0 else _money(request.data.get("amount"))
            currency = str(request.data.get("currency") or "XOF").upper()
            if not re.fullmatch(r"[A-Z]{3}", currency):
                raise ValueError("Devise invalide.")
        except ValueError as exc:
            return error_response(str(exc))

        with transaction.atomic():
            offer = get_object_or_404(CommercialOffer.objects.select_for_update(), pk=offer_id)
            # Append-only history: never rewrite an already-used price or invoice.
            PriceOption.objects.filter(
                offer=offer, term_months=term, seats=seats, is_active=True,
            ).update(is_active=False)
            option = PriceOption(
                offer=offer, term_months=term, seats=seats, amount=amount,
                currency=currency, created_by=request.user,
            )
            try:
                option.full_clean()
                option.save()
            except (ValidationError, IntegrityError):
                transaction.set_rollback(True)
                return error_response("Combinaison de prix invalide.", status_code=400)
        log_audit_event("subscription_price_updated", user=request.user, request=request, metadata={
            "offer_id": offer.pk, "price_id": option.pk, "term_months": term, "seats": seats,
        })
        return success_response("Nouveau tarif enregistré.", _price_dict(option), status_code=201)


class SuperadminPriceDetailView(_SuperadminOnly):
    """Withdraw a rate without deleting it or altering existing contracts."""
    def patch(self, request, price_id):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        if request.data.get("is_active") is not False:
            return error_response("Seul le retrait d'un tarif est autorisé.")
        with transaction.atomic():
            price = get_object_or_404(PriceOption.objects.select_for_update(), pk=price_id)
            if not price.is_active:
                return error_response("Ce tarif est déjà retiré.", status_code=409)
            price.is_active = False
            price.save(update_fields=["is_active"])
        log_audit_event("subscription_price_withdrawn", user=request.user, request=request,
                        metadata={"price_id": price.pk, "offer_id": price.offer_id})
        return success_response("Tarif retiré du catalogue.", _price_dict(price))


class SuperadminOrganisationsView(_SuperadminOnly):
    """Safe selector for subscription assignment; never exposes private members."""
    def get(self, request):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        schools = Institution.objects.filter(is_active=True).order_by("name").values("id", "name")[:250]
        companies = Enterprise.objects.order_by("company_name").values("id", "company_name")[:250]
        return success_response("Organisations éligibles.", {
            "institutions": list(schools),
            "enterprises": list(companies),
        })


class SuperadminAssignmentsView(_SuperadminOnly):
    """Manual activation only. No payment is collected or implied."""
    def get(self, request):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        entries = BusinessSubscription.objects.select_related(
            "price_option__offer", "institution", "enterprise",
        )[:100]
        return success_response("Abonnements attribués.", [_subscription_dict(s) for s in entries])

    def post(self, request):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        try:
            price_id = _integer(request.data.get("price_option_id"))
            institution_id = request.data.get("institution_id")
            enterprise_id = request.data.get("enterprise_id")
            if bool(institution_id) == bool(enterprise_id):
                raise ValueError("Sélectionnez exactement un établissement ou une entreprise.")
            scope = "institution" if institution_id else "enterprise"
            owner_id = _integer(institution_id or enterprise_id)
            starts = _date(request.data.get("starts_at") or timezone.localdate().isoformat())
        except ValueError as exc:
            return error_response(str(exc))

        with transaction.atomic():
            option = get_object_or_404(
                PriceOption.objects.select_related("offer"), pk=price_id, is_active=True,
                offer__is_active=True,
            )
            if option.offer.audience not in ("all", scope):
                return error_response("Offre indisponible pour ce type d'organisation.", status_code=403)
            required_unit = "publications" if scope == "enterprise" else "accounts"
            if option.offer.quota_unit != required_unit:
                return error_response("La capacité de cette offre ne correspond pas à l'organisation.", status_code=403)
            target = (
                get_object_or_404(Institution, pk=owner_id) if scope == "institution"
                else get_object_or_404(Enterprise, pk=owner_id)
            )
            filter_kwargs = {"institution": target} if scope == "institution" else {"enterprise": target}
            # Never replace history; old expired rows receive a terminal state.
            BusinessSubscription.objects.filter(
                **filter_kwargs, status="active", ends_at__lte=timezone.localdate(),
            ).update(status="ended")
            if BusinessSubscription.objects.filter(
                **filter_kwargs, status__in=("active", "scheduled"),
                ends_at__gt=timezone.localdate(),
            ).exists():
                return error_response("Un abonnement actif ou programmé existe déjà pour cette organisation.", status_code=409)
            if option.term_months == 0:
                try:
                    amount = _money(request.data.get("quoted_amount"))
                    ends = _date(request.data.get("ends_at"))
                except ValueError as exc:
                    transaction.set_rollback(True)
                    return error_response(str(exc))
            else:
                amount = option.amount
                ends = _plus_months(starts, option.term_months)
            if ends <= starts:
                transaction.set_rollback(True)
                return error_response("La fin doit être postérieure au début.")
            entry = BusinessSubscription(
                price_option=option, amount=amount, currency=option.currency,
                offer_name=option.offer.name, seats=option.seats,
                quota_unit=option.offer.quota_unit,
                term_months=option.term_months, starts_at=starts, ends_at=ends,
                created_by=request.user, **filter_kwargs,
            )
            try:
                entry.full_clean()
                entry.save()
            except (ValidationError, IntegrityError):
                transaction.set_rollback(True)
                return error_response("Attribution non valide.", status_code=409)
        log_audit_event("subscription_assigned", user=request.user, request=request,
                        metadata={"subscription_id": entry.pk, "scope": scope, "organisation_id": owner_id})
        return success_response("Abonnement attribué manuellement.", _subscription_dict(entry), status_code=201)


class SuperadminAssignmentDetailView(_SuperadminOnly):
    def patch(self, request, subscription_id):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        state = request.data.get("status")
        if state not in ("suspended", "ended"):
            return error_response("Seule la suspension ou clôture est autorisée ici.")
        with transaction.atomic():
            entry = get_object_or_404(
                BusinessSubscription.objects.select_for_update(), pk=subscription_id,
            )
            if entry.status not in ("active", "scheduled"):
                return error_response("Cet abonnement n'est plus actif ou programmé.", status_code=409)
            entry.status = state
            entry.save(update_fields=["status"])
        log_audit_event("subscription_state_changed", user=request.user, request=request,
                        metadata={"subscription_id": entry.pk, "status": state})
        entry = BusinessSubscription.objects.select_related(
            "price_option__offer", "institution", "enterprise",
        ).get(pk=subscription_id)
        return success_response("Statut mis à jour.", _subscription_dict(entry))


class SuperadminTopUpView(_SuperadminOnly):
    """Add capacity to the existing contract without modifying its original price."""
    def post(self, request, subscription_id):
        if not self._guard(request):
            return error_response("Superadmin requis.", status_code=403)
        try:
            quantity = _integer(request.data.get("quantity"))
            amount = _money(request.data.get("amount"))
            note = str(request.data.get("note") or "").strip()
            if len(note) > 255:
                raise ValueError("Note trop longue.")
        except ValueError as exc:
            return error_response(str(exc))
        with transaction.atomic():
            contract = get_object_or_404(
                BusinessSubscription.objects.select_for_update(), pk=subscription_id,
            )
            today = timezone.localdate()
            if contract.status not in ("active", "scheduled") or not contract.starts_at <= today < contract.ends_at:
                return error_response("Abonnement non actif : capacité supplémentaire impossible.", status_code=409)
            extra = SubscriptionTopUp.objects.create(
                subscription=contract, quantity=quantity, amount=amount,
                currency=contract.currency, note=note, created_by=request.user,
            )
        log_audit_event("subscription_capacity_added", user=request.user, request=request, metadata={
            "subscription_id": contract.pk, "topup_id": extra.pk, "quantity": quantity,
        })
        return success_response("Capacité ajoutée sans modifier le contrat d'origine.", {
            "id": extra.pk, "quota": quota_summary(contract),
        }, status_code=201)


class InstitutionSeatsView(_WebOnly):
    """School admin manages billing seats; cannot change another school's members."""
    def _school(self, request):
        role, institution = _organisation_for(request.user)
        return institution if role == "institution" and request.user.is_active and not request.user.is_banned else None

    def get(self, request):
        school = self._school(request)
        if school is None:
            return error_response("Administrateur établissement requis.", status_code=403)
        contract = current_contract(institution=school)
        members = []
        for role, qs in (
            ("student", StudentInstitution.objects.filter(institution=school).select_related("student__user")),
            ("alumni", AlumniInstitution.objects.filter(institution=school).select_related("alumni__user")),
        ):
            for link in qs.order_by("-id")[:250]:
                user = link.student.user if role == "student" else link.alumni.user
                members.append({"id": link.pk, "role": role, "name": user.get_full_name() or user.username,
                                "seat_enabled": link.seat_enabled, "user_active": user.is_active})
        return success_response("Comptes de l'établissement.", {
            "quota": quota_summary(contract) if contract else None,
            "members": members,
        })

    def patch(self, request):
        school = self._school(request)
        if school is None:
            return error_response("Administrateur établissement requis.", status_code=403)
        role = request.data.get("role")
        value = request.data.get("seat_enabled")
        try:
            seat_id = _integer(request.data.get("id"))
        except ValueError as exc:
            return error_response(str(exc))
        if role not in ("student", "alumni") or not isinstance(value, bool):
            return error_response("Compte ou statut incorrect.")
        link_model = StudentInstitution if role == "student" else AlumniInstitution
        with transaction.atomic():
            lock_institution(school.pk)
            link = link_model.objects.select_for_update().filter(pk=seat_id, institution=school).first()
            if link is None:
                return error_response("Compte introuvable dans votre établissement.", status_code=404)
            if value and not link.seat_enabled:
                user = link.student.user if role == "student" else link.alumni.user
                if user.is_active:
                    try:
                        require_available_school_seat(school)
                    except QuotaExceeded as exc:
                        return error_response(str(exc), status_code=409)
            link.seat_enabled = value
            link.save(update_fields=["seat_enabled"])
        log_audit_event("institution_seat_updated", user=request.user, request=request, metadata={
            "institution_id": school.pk, "role": role, "seat_id": seat_id, "enabled": value,
        })
        return success_response("Compte mis à jour.", {"id": seat_id, "seat_enabled": value})

