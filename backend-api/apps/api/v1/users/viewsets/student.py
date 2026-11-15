from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.establishments.pagination import StandardResultsSetPagination
from apps.api.v1.users.models import Student
from apps.api.v1.users.serializers import StudentSerializer
from apps.api.v1.establishments.models import StudentInstitution, PromotionMembership
from apps.api.v1.establishments.serializers import PromotionListSerializer, InstitutionListSerializer


class StudentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    # Uniquement pour l'introspection de schéma (drf-yasg) — le comportement
    # réel est dans get_queryset().
    queryset = Student.objects.none()
    serializer_class = StudentSerializer

    def list(self, request):
        """
        GET /api/v1/users/students/
        """
        qs = Student.objects.select_related("user").all().order_by("id")
        page = self.paginate_queryset(qs)
        serializer = StudentSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response("Liste des étudiants récupérée avec succès.", data=serializer.data)

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/users/students/{id}/
        """
        try:
            student = Student.objects.select_related("user").get(pk=pk)
        except Student.DoesNotExist:
            return error_response("Étudiant introuvable.", status_code=404)

        serializer = StudentSerializer(student)
        return success_response("Étudiant récupéré avec succès.", data=serializer.data)

    @action(detail=False, methods=["get"], url_path="profile")
    def profile(self, request):
        """
        GET /api/v1/users/students/profile/
        """
        user = request.user
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return error_response("Profil étudiant introuvable.", status_code=404)

        serializer = StudentSerializer(student)
        return success_response("Profil étudiant récupéré avec succès.", data=serializer.data)

    @action(detail=False, methods=["patch"], url_path="update-profile-fields")
    def update_profile_fields(self, request):
        """
        PATCH /api/v1/users/students/update-profile-fields/
        """
        user = request.user
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return error_response("Profil étudiant introuvable.", status_code=404)

        fields = {
            "skills": request.data.get("skills", []),
            "interests": request.data.get("interests", []),
            "preferences": request.data.get("preferences", []),
            "sectors": request.data.get("sectors", []),
        }

        for field_name, ids in fields.items():
            if ids:
                try:
                    getattr(student, field_name).set(ids)
                except Exception as e:
                    return error_response(
                        f"Erreur lors de la mise à jour de {field_name} : {str(e)}",
                        status_code=400,
                    )

        student.save()
        return success_response("Profil mis à jour avec succès.")

    @action(detail=False, methods=["get"], url_path="promotions")
    def my_promotions(self, request):
        """
        GET /api/v1/users/students/promotions/
        Récupère les promotions de l'étudiant connecté, filtrées par établissements actifs.
        """
        user = request.user
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return error_response("Profil étudiant introuvable.", status_code=404)

        active_institution_ids = StudentInstitution.objects.filter(
            student=student, is_active=True
        ).values_list('institution_id', flat=True)

        memberships = PromotionMembership.objects.filter(
            student=student,
            is_approved=True,
            promotion__institution_id__in=active_institution_ids,
        ).select_related('promotion__institution')

        promotions = [m.promotion for m in memberships]
        serializer = PromotionListSerializer(promotions, many=True, context={'request': request})
        return success_response("Promotions de l'étudiant récupérées avec succès.", data=serializer.data)

    @action(detail=False, methods=["get"], url_path="institutions")
    def my_institutions(self, request):
        """
        GET /api/v1/users/students/institutions/
        Récupère les établissements de l'étudiant connecté avec is_active dans my_membership.
        """
        user = request.user
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return error_response("Profil étudiant introuvable.", status_code=404)

        links = StudentInstitution.objects.filter(
            student=student
        ).select_related('institution')

        institution_list = [si.institution for si in links]

        # Construire my_membership_map en une seule passe (évite le N+1
        # que ferait get_my_membership() sur chaque établissement).
        membership_map = {
            si.institution_id: {
                'type': 'student',
                'joined_at': si.joined_at,
                'is_primary': si.is_primary,
                'is_active': si.is_active,
            }
            for si in links
        }

        serializer = InstitutionListSerializer(
            institution_list,
            many=True,
            context={'request': request, 'my_membership_map': membership_map},
        )
        return success_response(
            "Établissements de l'étudiant récupérés avec succès.",
            data=serializer.data,
        )