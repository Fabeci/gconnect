# apps/api/v1/establishments/permissions.py

from rest_framework.permissions import BasePermission

class IsInstitutionAdminOrPromotionDelegate(BasePermission):
    message = "Vous n'avez pas la permission d'effectuer cette action."

    def has_permission(self, request, view):
        # Vérifie si l'utilisateur est authentifié et a un rôle général autorisé
        return request.user and request.user.is_authenticated
    
    print("Okkkkkkkkkkkkkkkkkkk", "")
    def has_object_permission(self, request, view, obj):
        print("has_object_permission called")
        user = request.user

        # Vérifie si c'est un admin d'établissement lié
        if user.role == 'etablissement':
            if hasattr(user, 'institution_profile'):
                if user.institution_profile == obj.promotion.institution:
                    return True

        # Vérifie si c'est un étudiant délégué dans la promotion
        if user.role == 'student':
            student = getattr(user, 'student_profile', None)
            if student and obj.promotion.members.filter(student=student, is_delegate=True).exists():
                return True

        return False
    

# class CanAccessInstitutionPromotions(BasePermission):
#     def has_permission(self, request, view):
#         institution_id = view.kwargs.get('institution_pk')  # ou institution_id

#         if request.user.is_authenticated:
#             if hasattr(request.user, 'student_profile'):
#         # Si l'étudiant appartient à plusieurs institutions
#                 student = request.user.student_profile
#                 return student.institutions.filter(id=institution_id).exists()

#             if hasattr(request.user, 'institutionadmin_profile'):
#                 admin = request.user.institutionadmin_profile
#                 return str(admin.institution.id) == institution_id

#         return False

class IsInstitutionManager(BasePermission):
    """Only the institution's administrator (or a platform superadmin) may edit it."""

    message = "Seul l'administrateur de cet établissement peut le modifier."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "role", None) == "superAdmin":
            return True
        if user.role != "etablissement":
            return False
        admin = getattr(user, "institution_admin_profile", None)
        return bool(admin and admin.institution_id == obj.pk and admin.institution.is_active)


class IsInstitutionScopedManager(BasePermission):
    """Restrict management actions to platform admins or the linked institution.

    The target may be a Promotion, PromotionMembership, account order or any
    object with an `institution_id` or `promotion.institution_id` field.
    Creation additionally requires serializer validation of the target scope.
    """

    message = "Action réservée à l'administrateur de cet établissement."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.role == "superAdmin":
            return True
        if user.role != "etablissement":
            return False
        admin = getattr(user, "institution_admin_profile", None)
        return bool(admin and admin.institution.is_active)

    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False
        if request.user.role == "superAdmin":
            return True
        admin = request.user.institution_admin_profile
        institution_id = getattr(obj, "institution_id", None)
        if institution_id is None:
            promotion = getattr(obj, "promotion", None)
            institution_id = getattr(promotion, "institution_id", None)
        return institution_id == admin.institution_id
