"""E24 enterprise-owned offers, candidates and publications for the privileged web portal.

Every query is scoped to the authenticated enterprise profile. Mobile bearer
tokens cannot authenticate because this API only accepts WebToken sessions.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.posts.models import Application, Opportunity, Post
from apps.api.v1.subscriptions.quotas import consume_enterprise_publication
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


class EnterpriseOnlyView(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def company(self, request):
        user = request.user
        if user.role != "enterprise" or not user.is_active or user.is_banned:
            return None
        return getattr(user, "enterprise_profile", None)


def _offer_row(offer):
    return {
        "id": offer.pk, "post_id": offer.post_id, "title": offer.post.title,
        "description": offer.post.content, "category": offer.category,
        "contract_type": offer.contract_type, "work_mode": offer.work_mode,
        "location_city": offer.location_city, "location_country": offer.location_country,
        "status": offer.status, "is_archived": offer.post.is_archived,
        "deadline": offer.deadline.isoformat() if offer.deadline else None,
        "duration_months": offer.duration_months,
        "currency": offer.currency, "salary_min": offer.salary_min,
        "salary_max": offer.salary_max,
        "applications_count": getattr(offer, "applications_count", None),
        "created_at": offer.post.created_at.isoformat(),
    }


def _offer_errors(error):
    if hasattr(error, "message_dict"):
        return {key: [str(message) for message in messages]
                for key, messages in error.message_dict.items()}
    return {"detail": [str(error)]}


class EnterpriseOffersView(EnterpriseOnlyView):
    def get(self, request):
        company = self.company(request)
        if not company:
            return error_response("Espace Entreprise requis.", status_code=403)
        rows = Opportunity.objects.filter(enterprise=company, post__author=request.user)\
            .select_related("post").annotate(applications_count=Count("applications"))\
            .order_by("-post__created_at")[:200]
        return success_response("Offres de votre entreprise.", [_offer_row(offer) for offer in rows])

    @transaction.atomic
    def post(self, request):
        company = self.company(request)
        if not company:
            return error_response("Espace Entreprise requis.", status_code=403)
        data = request.data
        title = str(data.get("title") or "").strip()
        description = str(data.get("description") or "").strip()
        if not 3 <= len(title) <= 255 or len(description) > 5000:
            return error_response("Titre (3 à 255 caractères) ou description invalide.", status_code=400)
        post = Post(
            author=request.user, title=title, content=description,
            post_type=Post.PostType.OPPORTUNITY, audience=Post.Audience.PUBLIC,
        )
        try:
            post.full_clean()
            post.save()
            offer = Opportunity(
                post=post, enterprise=company,
                category=str(data.get("category") or Opportunity.Category.JOB),
                contract_type=str(data.get("contract_type") or ""),
                work_mode=str(data.get("work_mode") or Opportunity.WorkMode.ONSITE),
                location_city=str(data.get("location_city") or "").strip(),
                location_country=str(data.get("location_country") or "").strip(),
                duration_months=data.get("duration_months") or None,
                deadline=data.get("deadline") or None,
            )
            offer.full_clean()
            offer.save()
            consume_enterprise_publication(company, post)
        except (DjangoValidationError, ValueError, TypeError) as exc:
            transaction.set_rollback(True)
            return error_response("Champs de l'offre invalides.", status_code=400, errors=_offer_errors(exc))
        return success_response("Offre publiée.", _offer_row(offer), status_code=201)


class EnterpriseOfferDetailView(EnterpriseOnlyView):
    @transaction.atomic
    def patch(self, request, offer_id):
        company = self.company(request)
        if not company:
            return error_response("Espace Entreprise requis.", status_code=403)
        offer = Opportunity.objects.select_for_update().select_related("post").filter(
            pk=offer_id, enterprise=company, post__author=request.user,
        ).first()
        if not offer:
            return error_response("Offre introuvable.", status_code=404)
        data = request.data
        allowed = {"status", "title", "description", "deadline", "is_archived"}
        if not set(data.keys()) or set(data.keys()) - allowed:
            return error_response("Champs de modification invalides.", status_code=400)
        if "status" in data:
            if data["status"] not in (Opportunity.Status.OPEN, Opportunity.Status.CLOSED):
                return error_response("Statut invalide.", status_code=400)
            offer.status = data["status"]
        if "title" in data:
            offer.post.title = str(data["title"] or "").strip()
            if not 3 <= len(offer.post.title) <= 255:
                return error_response("Titre invalide.", status_code=400)
        if "description" in data:
            offer.post.content = str(data["description"] or "")
        if "deadline" in data:
            offer.deadline = data["deadline"] or None
        if "is_archived" in data:
            if not isinstance(data["is_archived"], bool):
                return error_response("Archivage invalide.", status_code=400)
            offer.post.is_archived = data["is_archived"]
        try:
            offer.post.full_clean()
            offer.full_clean()
        except DjangoValidationError as exc:
            return error_response("Champs de l'offre invalides.", status_code=400, errors=_offer_errors(exc))
        offer.post.save()
        offer.save()
        return success_response("Offre mise à jour.", _offer_row(offer))


def _application_row(application):
    candidate = application.user
    return {
        "id": application.pk, "offer_id": application.opportunity_id,
        "offer_title": application.opportunity.post.title,
        "candidate_name": candidate.get_full_name() or candidate.username,
        "candidate_email": candidate.email, "status": application.status,
        "cover_letter": application.cover_letter,
        "portfolio_url": application.portfolio_url,
        "has_resume": bool(application.resume),
        "created_at": application.created_at.isoformat(),
    }


class EnterpriseApplicationsView(EnterpriseOnlyView):
    def get(self, request):
        company = self.company(request)
        if not company:
            return error_response("Espace Entreprise requis.", status_code=403)
        applications = Application.objects.filter(
            opportunity__enterprise=company, opportunity__post__author=request.user,
        ).select_related("user", "opportunity__post").order_by("-created_at")[:300]
        return success_response("Candidatures reçues.", [_application_row(item) for item in applications])


class EnterpriseApplicationDetailView(EnterpriseOnlyView):
    @transaction.atomic
    def patch(self, request, application_id):
        company = self.company(request)
        if not company:
            return error_response("Espace Entreprise requis.", status_code=403)
        application = Application.objects.select_for_update().select_related(
            "user", "opportunity__post",
        ).filter(pk=application_id, opportunity__enterprise=company,
                 opportunity__post__author=request.user).first()
        if not application:
            return error_response("Candidature introuvable.", status_code=404)
        if set(request.data.keys()) != {"status"}:
            return error_response("Seul le statut peut être modifié.", status_code=400)
        value = request.data.get("status")
        if value not in dict(Application.STATUS):
            return error_response("Statut de candidature invalide.", status_code=400)
        application.status = value
        application.save(update_fields=["status", "updated_at"])
        return success_response("Candidature mise à jour.", _application_row(application))


class EnterprisePublicationsView(EnterpriseOnlyView):
    def get(self, request):
        company = self.company(request)
        if not company:
            return error_response("Espace Entreprise requis.", status_code=403)
        posts = Post.objects.filter(author=request.user).order_by("-created_at")[:150]
        return success_response("Publications de votre entreprise.", [
            {"id": post.pk, "title": post.title, "content": post.content,
             "post_type": post.post_type, "views_count": post.views_count,
             "reactions_count": post.reactions_count, "comments_count": post.comments_count,
             "is_archived": post.is_archived, "created_at": post.created_at.isoformat()}
            for post in posts
        ])

    @transaction.atomic
    def post(self, request):
        company = self.company(request)
        if not company:
            return error_response("Espace Entreprise requis.", status_code=403)
        title = str(request.data.get("title") or "").strip()
        content = str(request.data.get("content") or "").strip()
        if not 3 <= len(title) <= 255 or not content or len(content) > 5000:
            return error_response("Titre ou contenu invalide.", status_code=400)
        post = Post(
            author=request.user, title=title, content=content,
            post_type=Post.PostType.DISCUSSION, audience=Post.Audience.PUBLIC,
        )
        post.full_clean()
        post.save()
        consume_enterprise_publication(company, post)
        return success_response("Publication créée.", {"id": post.pk}, status_code=201)

