"""E34 · Répertoire des utilisateurs, lecture seule, réservé au Superadmin MFA.

Aucun rôle "recruteur" n'existe dans User.ROLES. L'espace Entreprises conserve
ses recruteurs métiers; la liste des identités reflète exclusivement les rôles
réellement enregistrés en base. Ne retourne aucune donnée confidentielle de
MFA, mots de passe, documents d'identité, dates de naissance ou CV.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.permissions import IsSuperAdmin
from apps.api.v1.core.responses import success_response, error_response
from apps.api.v1.users.models import User
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


class SuperadminUserDirectoryE34(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        search = str(request.query_params.get("search", "")).strip()[:120]
        role = str(request.query_params.get("role", "all")).strip()
        status = str(request.query_params.get("status", "all")).strip()
        roles = {key for key, _ in User.ROLES}
        if role not in roles | {"all"} or status not in ("all", "active", "pending", "banned"):
            return error_response("Filtre de comptes invalide.", status_code=400)
        try:
            page = int(request.query_params.get("page", "1"))
            size = int(request.query_params.get("page_size", "12"))
        except (TypeError, ValueError):
            return error_response("Pagination invalide.", status_code=400)
        if page < 1 or size < 1 or size > 50:
            return error_response("Pagination invalide.", status_code=400)

        all_users = User.objects.all()
        summary_by_role = {
            line["role"]: line["total"]
            for line in all_users.values("role").annotate(total=Count("id"))
        }
        since = timezone.now() - timedelta(days=30)
        summary = {
            "total": all_users.count(),
            "active": all_users.filter(is_active=True, is_banned=False).count(),
            "students": summary_by_role.get("student", 0),
            "alumni": summary_by_role.get("alumni", 0),
            "enterprises": summary_by_role.get("enterprise", 0),
            "institution_admins": summary_by_role.get("etablissement", 0),
            "superadmins": summary_by_role.get("superAdmin", 0),
            "pending": all_users.filter(is_active=False, is_banned=False).count(),
            "banned": all_users.filter(is_banned=True).count(),
            "joined_30_days": all_users.filter(date_joined__gte=since).count(),
        }

        query = all_users
        if search:
            query = query.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(location__icontains=search)
            )
        if role != "all":
            query = query.filter(role=role)
        if status == "active":
            query = query.filter(is_active=True, is_banned=False)
        elif status == "pending":
            query = query.filter(is_active=False, is_banned=False)
        elif status == "banned":
            query = query.filter(is_banned=True)

        query = query.order_by("-date_joined", "-pk")
        count = query.count()
        pages = max(1, (count + size - 1) // size)
        if page > pages:
            return error_response("Page inexistante.", status_code=404)

        accounts = list(
            query.select_related(
                "enterprise_profile", "institution_admin_profile__institution",
                "alumni_profile__institution",
            ).prefetch_related("student_profile__institutions")[
                (page - 1) * size:page * size
            ]
        )
        results = []
        for user in accounts:
            association = ""
            if user.role == "enterprise":
                company = getattr(user, "enterprise_profile", None)
                association = company.company_name if company else ""
            elif user.role == "etablissement":
                admin = getattr(user, "institution_admin_profile", None)
                association = admin.institution.name if admin and admin.institution else ""
            elif user.role == "alumni":
                profile = getattr(user, "alumni_profile", None)
                association = profile.institution.name if profile and profile.institution else ""
            elif user.role == "student":
                profile = getattr(user, "student_profile", None)
                if profile:
                    names = [x.name for x in profile.institutions.all()]
                    association = names[0] if len(names) == 1 else (
                        f"{len(names)} établissements" if len(names) > 1 else ""
                    )

            results.append({
                "id": user.pk,
                "display_name": user.get_full_name().strip() or user.username,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "role_label": user.get_role_display(),
                "is_active": bool(user.is_active),
                "is_banned": bool(user.is_banned),
                "location": user.location or "",
                "association": association,
                "joined_at": user.date_joined.isoformat(),
                "last_login_at": user.last_login.isoformat() if user.last_login else None,
            })

        response = success_response("Répertoire des comptes G-Connect.", {
            "summary": summary,
            "results": results,
            "count": count,
            "page": page,
            "page_size": size,
            "pages": pages,
            "roles": [
                {"value": key, "label": label}
                for key, label in User.ROLES
            ],
        })
        response["Cache-Control"] = "no-store"
        return response
