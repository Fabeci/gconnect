# permissions.py
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Réservé aux comptes `role == 'superAdmin'` — back-office avancé."""
    message = "Réservé aux super-administrateurs."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "superAdmin")
