from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.establishments.pagination import StandardResultsSetPagination
from apps.api.v1.users.models import Alumni
from apps.api.v1.users.serializers import AlumniSerializer
from apps.api.v1.establishments.serializers import InstitutionListSerializer, PromotionListSerializer
from apps.api.v1.establishments.models import AlumniInstitution, AlumniPromotionMembership


class AlumniViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    # Uniquement pour l'introspection de schéma (drf-yasg) — le comportement
    # réel est dans get_queryset().
    queryset = Alumni.objects.none()
    serializer_class = AlumniSerializer

    def list(self, request):
        """
        GET /api/v1/users/alumni/
        """
        qs = Alumni.objects.select_related("user").all().order_by("id")
        page = self.paginate_queryset(qs)
        serializer = AlumniSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response("Liste des alumni récupérée avec succès.", data=serializer.data)

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/users/alumni/{id}/
        """
        try:
            alumni = Alumni.objects.select_related("user").get(pk=pk)
        except Alumni.DoesNotExist:
            return error_response("Alumni introuvable.", status_code=404)

        serializer = AlumniSerializer(alumni)
        return success_response("Alumni récupéré avec succès.", data=serializer.data)

    @action(detail=False, methods=["get"], url_path="profile")
    def profile(self, request):
        """
        GET /api/v1/users/alumni/profile/
        """
        user = request.user
        try:
            alumni = user.alumni_profile
        except Alumni.DoesNotExist:
            return error_response("Profil alumni introuvable.", status_code=404)

        serializer = AlumniSerializer(alumni)
        return success_response("Profil alumni récupéré avec succès.", data=serializer.data)

    @action(detail=False, methods=["patch"], url_path="update-profile-fields")
    def update_profile_fields(self, request):
        """
        PATCH /api/v1/users/alumni/update-profile-fields/
        """
        user = request.user
        try:
            alumni = user.alumni_profile
        except Alumni.DoesNotExist:
            return error_response("Profil alumni introuvable.", status_code=404)

        fields = {
            "skills": request.data.get("skills", []),
            "interests": request.data.get("interests", []),
            "preferences": request.data.get("preferences", []),
            "sectors": request.data.get("sectors", []),
        }

        for field_name, ids in fields.items():
            if ids:
                try:
                    getattr(alumni, field_name).set(ids)
                except Exception as e:
                    return error_response(
                        f"Erreur lors de la mise à jour de {field_name} : {str(e)}",
                        status_code=400,
                    )

        alumni.save()
        return success_response("Profil alumni mis à jour avec succès.")

    @action(detail=False, methods=["get"], url_path="promotions")
    def my_promotions(self, request):
        """
        GET /api/v1/users/alumni/promotions/
        Récupère les promotions de l'alumni connecté, filtrées par établissements actifs.
        """
        user = request.user
        try:
            alumni = user.alumni_profile
        except Alumni.DoesNotExist:
            return error_response("Profil alumni introuvable.", status_code=404)

        active_institution_ids = AlumniInstitution.objects.filter(
            alumni=alumni, is_active=True
        ).values_list('institution_id', flat=True)

        memberships = AlumniPromotionMembership.objects.filter(
            alumni=alumni,
            is_approved=True,
            promotion__institution_id__in=active_institution_ids,
        ).select_related('promotion__institution')

        promotions = [m.promotion for m in memberships]
        serializer = PromotionListSerializer(promotions, many=True, context={'request': request})
        return success_response("Promotions de l'alumni récupérées avec succès.", data=serializer.data)

    @action(detail=False, methods=["get"], url_path="institution")
    def my_institution(self, request):
        """
        GET /api/v1/users/alumni/institution/
        Récupère l'établissement de l'alumni connecté avec is_active dans my_membership.
        """
        user = request.user
        try:
            alumni = user.alumni_profile
        except Alumni.DoesNotExist:
            return error_response("Profil alumni introuvable.", status_code=404)

        if not alumni.institution:
            return error_response("Aucun établissement trouvé.", status_code=404)

        institution = alumni.institution
        # Chercher le lien AlumniInstitution pour exposer is_active
        link = AlumniInstitution.objects.filter(
            alumni=alumni, institution=institution
        ).first()

        membership_map = {}
        if link:
            membership_map[institution.id] = {
                'type': 'alumni',
                'joined_at': link.joined_at,
                'is_active': link.is_active,
            }
        else:
            # Fallback : alumni créé avant AlumniInstitution, considéré actif
            membership_map[institution.id] = {
                'type': 'alumni',
                'is_active': True,
            }

        serializer = InstitutionListSerializer(
            institution,
            context={'request': request, 'my_membership_map': membership_map},
        )
        return success_response(
            "Établissement de l'alumni récupéré avec succès.",
            data=serializer.data,
        )
