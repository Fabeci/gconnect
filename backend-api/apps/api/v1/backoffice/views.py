# backoffice/views.py
"""
Back-office avancé (superAdmin) : file de modération des signalements,
gestion des comptes (suspension/bannissement), et consultation du journal
d'audit. Les CRUD établissements/promotions existent déjà via les endpoints
`establishments` (réservés aux admins d'établissement / superAdmin) — ce
module couvre spécifiquement le gap identifié : modération transversale.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.models import AuditLogEntry
from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import success_response, error_response
from apps.api.v1.establishments.models import Institution, Promotion
from apps.api.v1.establishments.pagination import StandardResultsSetPagination
from apps.api.v1.posts.models import Application, Comment, Opportunity, Post, Reaction
from apps.api.v1.users.models import EstablishmentWebSession
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication

from . import imports as bulk_imports
from .models import ImportJob, Report
from .serializers import (
    AdminUserSerializer, ImportJobSerializer, ReportCreateSerializer, ReportSerializer,
)

User = get_user_model()


class ReportViewSet(viewsets.ModelViewSet):
    """
    POST   /backoffice/reports/            — n'importe quel utilisateur connecté signale.
    GET    /backoffice/reports/?status=    — file de modération (superAdmin uniquement).
    POST   /backoffice/reports/{id}/dismiss/
    POST   /backoffice/reports/{id}/action/  {hide_post: bool, ban_user: bool, reason}
    """
    pagination_class = StandardResultsSetPagination
    queryset = Report.objects.select_related("reporter", "reported_user", "post", "comment", "reviewed_by")

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    def get_serializer_class(self):
        return ReportCreateSerializer if self.action == "create" else ReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(reporter=request.user)
        detail = ReportSerializer(report, context=self.get_serializer_context())
        return Response(detail.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        report = self.get_object()
        report.status = Report.Status.DISMISSED
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        log_audit_event("report_reviewed", user=request.user, request=request,
                         metadata={"report_id": report.id, "outcome": "dismissed"})
        return success_response("Signalement rejeté.", ReportSerializer(report).data)

    @action(detail=True, methods=["post"])
    def action_taken(self, request, pk=None):
        report = self.get_object()
        hide_post = bool(request.data.get("hide_post"))
        ban_user = bool(request.data.get("ban_user"))
        reason = (request.data.get("reason") or "").strip()

        if hide_post and report.post_id:
            report.post.is_hidden_by_admin = True
            report.post.hidden_reason = reason or f"Signalement #{report.id}"
            report.post.save(update_fields=["is_hidden_by_admin", "hidden_reason"])
            log_audit_event("post_hidden", user=request.user, request=request,
                             metadata={"post_id": report.post_id, "report_id": report.id, "reason": reason})

        target_user = report.reported_user or (report.post.author if report.post_id else None)
        if ban_user and target_user:
            target_user.is_banned = True
            target_user.banned_reason = reason or f"Signalement #{report.id}"
            target_user.banned_at = timezone.now()
            target_user.save(update_fields=["is_banned", "banned_reason", "banned_at"])
            Token.objects.filter(user=target_user).delete()
            EstablishmentWebSession.objects.filter(
                user=target_user, revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())
            log_audit_event("user_banned", user=request.user, request=request,
                             metadata={"target_user_id": target_user.id, "report_id": report.id, "reason": reason})

        report.status = Report.Status.ACTIONED
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return success_response("Action appliquée.", ReportSerializer(report).data)


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /backoffice/users/?search=&role=&banned=
    POST /backoffice/users/{id}/ban/    {reason}
    POST /backoffice/users/{id}/unban/
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminUserSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        search = self.request.query_params.get("search", "").strip()
        role = self.request.query_params.get("role")
        banned = self.request.query_params.get("banned")

        if search:
            qs = qs.filter(
                Q(username__icontains=search) | Q(email__icontains=search) |
                Q(first_name__icontains=search) | Q(last_name__icontains=search)
            )
        if role:
            qs = qs.filter(role=role)
        if banned is not None:
            qs = qs.filter(is_banned=banned.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def ban(self, request, pk=None):
        user = self.get_object()
        if user.role == "superAdmin":
            return error_response("Impossible de bannir un super-administrateur.", status_code=400)
        reason = (request.data.get("reason") or "").strip()
        user.is_banned = True
        user.banned_reason = reason
        user.banned_at = timezone.now()
        user.save(update_fields=["is_banned", "banned_reason", "banned_at"])
        Token.objects.filter(user=user).delete()
        EstablishmentWebSession.objects.filter(
            user=user, revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        log_audit_event("user_banned", user=request.user, request=request,
                         metadata={"target_user_id": user.id, "reason": reason})
        return success_response("Utilisateur banni.", AdminUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def unban(self, request, pk=None):
        user = self.get_object()
        user.is_banned = False
        user.banned_reason = ""
        user.banned_at = None
        user.save(update_fields=["is_banned", "banned_reason", "banned_at"])
        log_audit_event("user_unbanned", user=request.user, request=request,
                         metadata={"target_user_id": user.id})
        return success_response("Utilisateur débanni.", AdminUserSerializer(user).data)


class AdminAuditLogView(ListAPIView):
    """GET /backoffice/audit-log/?action=&user= — journal d'audit (superAdmin)."""
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = AuditLogEntry.objects.select_related("user").all()
        action_param = self.request.query_params.get("action")
        user_id = self.request.query_params.get("user")
        if action_param:
            qs = qs.filter(action=action_param)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        target = page if page is not None else qs
        data = [
            {
                "id": e.id,
                "action": e.action,
                "action_display": e.get_action_display(),
                "user_id": e.user_id,
                "user_name": (e.user.get_full_name() or e.user.username) if e.user else None,
                "ip_address": e.ip_address,
                "metadata": e.metadata,
                "created_at": e.created_at,
            }
            for e in target
        ]
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)


class ImportView(APIView):
    """
    POST /backoffice/imports/  multipart : file, import_type, institution (id, optionnel)
    Réservé aux admins d'établissement (pour leur propre établissement) et
    aux superAdmin (n'importe quel établissement, + import d'établissements
    eux-mêmes). Traitement synchrone — la réponse contient déjà le rapport
    complet (succès/erreurs par ligne).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import_type = request.data.get("import_type")
        if import_type not in (*bulk_imports.IMPORTERS.keys(), "establishments"):
            return error_response(
                "import_type invalide (attendu : students, alumni, promotions, establishments).",
                status_code=400,
            )

        uploaded = request.FILES.get("file")
        if not uploaded:
            return error_response("Fichier requis (.csv ou .xlsx).", status_code=400)

        user = request.user
        is_super = user.role == "superAdmin"
        institution = None

        if import_type == "establishments":
            if not is_super:
                return error_response("Réservé aux super-administrateurs.", status_code=403)
        else:
            institution_id = request.data.get("institution")
            if is_super:
                if not institution_id:
                    return error_response("Le champ 'institution' est requis.", status_code=400)
                institution = Institution.objects.filter(id=institution_id).first()
                if not institution:
                    return error_response("Établissement introuvable.", status_code=404)
            elif user.role == "etablissement" and hasattr(user, "institution_admin_profile"):
                institution = user.institution_admin_profile.institution
                if not institution.is_active:
                    return error_response("Établissement inactif.", status_code=403)
            else:
                return error_response("Réservé aux admins d'établissement et aux super-administrateurs.", status_code=403)

        try:
            rows = bulk_imports.parse_rows(uploaded)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)

        if import_type == "establishments":
            created, errors = bulk_imports.import_establishments(rows)
        else:
            created, errors = bulk_imports.IMPORTERS[import_type](rows, institution)

        job = ImportJob.objects.create(
            initiated_by=user,
            institution=institution,
            import_type=import_type,
            file_name=uploaded.name,
            total_rows=len(rows),
            success_count=len(created),
            error_count=len(errors),
            errors=errors,
            created_rows=created,
        )
        log_audit_event(
            "import_completed", user=user, request=request,
            metadata={"import_type": import_type, "total": len(rows), "success": len(created), "errors": len(errors)},
        )
        return success_response("Import terminé.", ImportJobSerializer(job).data)


class ImportJobListView(ListAPIView):
    """GET /backoffice/imports/ — historique des imports (scope selon le rôle)."""
    permission_classes = [IsAuthenticated]
    serializer_class = ImportJobSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        qs = ImportJob.objects.select_related("institution", "initiated_by")
        if user.role == "superAdmin":
            return qs
        if user.role == "etablissement" and hasattr(user, "institution_admin_profile"):
            institution = user.institution_admin_profile.institution
            return qs.filter(institution=institution) if institution.is_active else qs.none()
        return qs.none()


class AdminStatsView(APIView):
    """
    GET /backoffice/stats/
    Tableau de bord statistique — vue globale (superAdmin) ou restreinte à
    l'établissement (admin d'établissement). Toutes les métriques utilisent
    des requêtes groupées bornées (aggregate/annotate), jamais une requête
    par élément.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = user.role == "superAdmin"
        institution = None

        if not is_super:
            if user.role != "etablissement" or not hasattr(user, "institution_admin_profile"):
                return error_response("Réservé aux admins d'établissement et aux super-administrateurs.", status_code=403)
            institution = user.institution_admin_profile.institution
            if not institution.is_active:
                return error_response("Établissement inactif.", status_code=403)

        users_qs = User.objects.all() if is_super else User.objects.filter(
            Q(student_profile__institutions=institution) | Q(alumni_profile__institution=institution) |
            Q(institution_admin_profile__institution=institution)
        ).distinct()

        role_counts = dict(users_qs.values_list("role").annotate(c=Count("id")).order_by())
        users_stats = {
            "total": users_qs.count(),
            "students": role_counts.get("student", 0),
            "alumni": role_counts.get("alumni", 0),
            "enterprises": role_counts.get("enterprise", 0),
            "institution_admins": role_counts.get("etablissement", 0),
            "banned": users_qs.filter(is_banned=True).count(),
            "pending_activation": users_qs.filter(is_active=False).count(),
        }

        posts_qs = Post.objects.all() if is_super else Post.objects.filter(institution=institution)
        post_type_counts = dict(posts_qs.values_list("post_type").annotate(c=Count("id")).order_by())
        posts_stats = {
            "total": posts_qs.count(),
            "opportunities": post_type_counts.get(Post.PostType.OPPORTUNITY, 0),
            "events": post_type_counts.get(Post.PostType.EVENT, 0),
            "projects": post_type_counts.get(Post.PostType.PROJECT, 0),
            "hidden_by_admin": posts_qs.filter(is_hidden_by_admin=True).count(),
        }

        reactions_qs = Reaction.objects.all() if is_super else Reaction.objects.filter(post__institution=institution)
        comments_qs = Comment.objects.all() if is_super else Comment.objects.filter(post__institution=institution)

        promotions_qs = Promotion.objects.all() if is_super else Promotion.objects.filter(institution=institution)

        pending_reports = Report.objects.filter(status=Report.Status.PENDING)
        if not is_super:
            pending_reports = pending_reports.filter(
                Q(post__institution=institution) | Q(reported_user__in=users_qs)
            )

        window_start = timezone.now() - timedelta(days=30)
        signups_qs = users_qs.filter(date_joined__gte=window_start)
        signups_trend = list(
            signups_qs.annotate(day=TruncDate("date_joined"))
            .values("day").annotate(count=Count("id")).order_by("day")
        )

        data = {
            "scope": "global" if is_super else "institution",
            "institution_name": institution.name if institution else None,
            "users": users_stats,
            "institutions_count": Institution.objects.count() if is_super else None,
            "promotions_count": promotions_qs.count(),
            "posts": posts_stats,
            "engagement": {"reactions": reactions_qs.count(), "comments": comments_qs.count()},
            "reports_pending": pending_reports.count(),
            "signups_last_30_days": [
                {"date": row["day"].isoformat(), "count": row["count"]} for row in signups_trend
            ],
        }
        return success_response("Statistiques.", data)


class EnterpriseDashboardView(APIView):
    """GET /backoffice/enterprise-dashboard/ — exclusively the current company.

    Never accepts an enterprise ID from the browser. In particular, application
    statistics are bounded to opportunities authored by this account or explicitly
    linked to its Enterprise profile. No applicant personal data is returned.
    """
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != "enterprise":
            return error_response("Accès réservé aux entreprises.", status_code=403)
        enterprise = getattr(user, "enterprise_profile", None)
        if enterprise is None:
            return error_response("Profil Entreprise indisponible.", status_code=403)

        posts = Post.objects.filter(author=user)
        visible_posts = posts.filter(is_draft=False, is_archived=False, is_hidden_by_admin=False)
        own_opportunities = Opportunity.objects.filter(
            Q(enterprise=enterprise) | Q(enterprise__isnull=True, post__author=user),
        ).distinct()
        applications = Application.objects.filter(opportunity__in=own_opportunities)

        status_counts = dict(
            applications.values_list("status").annotate(total=Count("id")).order_by()
        )
        category_counts = dict(
            own_opportunities.values_list("category").annotate(total=Count("id")).order_by()
        )
        now = timezone.now()
        since = now - timedelta(days=30)

        offer_trend = list(
            own_opportunities.filter(post__created_at__gte=since)
            .annotate(day=TruncDate("post__created_at"))
            .values("day").annotate(count=Count("id")).order_by("day")
        )
        application_trend = list(
            applications.filter(created_at__gte=since)
            .annotate(day=TruncDate("created_at"))
            .values("day").annotate(count=Count("id")).order_by("day")
        )
        recent_offers = own_opportunities.select_related("post").annotate(
            application_count=Count("applications"),
        ).order_by("-post__created_at", "-pk")[:8]

        data = {
            "scope": "enterprise",
            "enterprise_id": enterprise.pk,
            "company_name": enterprise.company_name,
            "sector": enterprise.sector,
            "website": enterprise.website or "",
            "posts": {
                "total": visible_posts.count(),
                "drafts": posts.filter(is_draft=True).count(),
                "events": visible_posts.filter(post_type=Post.PostType.EVENT).count(),
                "projects": visible_posts.filter(post_type=Post.PostType.PROJECT).count(),
            },
            "opportunities": {
                "total": own_opportunities.count(),
                "open": own_opportunities.filter(status=Opportunity.Status.OPEN).count(),
                "closed": own_opportunities.filter(status=Opportunity.Status.CLOSED).count(),
                "by_category": category_counts,
                "recent": [{
                    "id": offer.pk,
                    "title": offer.post.title,
                    "category": offer.category,
                    "status": offer.status,
                    "created_at": offer.post.created_at.isoformat(),
                    "applications": offer.application_count,
                } for offer in recent_offers],
            },
            "applications": {
                "total": applications.count(),
                "by_status": status_counts,
            },
            "engagement": {
                "views": visible_posts.aggregate(total=Sum("views_count"))["total"] or 0,
                "reactions": Reaction.objects.filter(post__author=user).count(),
                "comments": Comment.objects.filter(post__author=user).count(),
            },
            "offers_last_30_days": [
                {"date": row["day"].isoformat(), "count": row["count"]}
                for row in offer_trend
            ],
            "applications_last_30_days": [
                {"date": row["day"].isoformat(), "count": row["count"]}
                for row in application_trend
            ],
        }
        return success_response("Tableau de bord de votre entreprise.", data)
