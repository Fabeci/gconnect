"""Password changes for MFA-verified G-Connect professional browser sessions.

Reuses the existing validated ChangePasswordView. It verifies the current
password, applies Django validators, revokes all web sessions and mobile tokens,
and requires a fresh sign-in with MFA. No password appears in logs or replies.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from apps.api.v1.core.responses import error_response
from apps.api.v1.users.views import ChangePasswordView
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


class ProfessionalPasswordChangeThrottle(UserRateThrottle):
    scope = "professional_password_change"
    rate = "6/min"


class ProfessionalPasswordChangeView(ChangePasswordView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ProfessionalPasswordChangeThrottle]

    def post(self, request):
        current = request.data.get("current_password")
        new = request.data.get("new_password")
        if not isinstance(current, str) or not isinstance(new, str):
            return error_response("Renseignez les deux mots de passe.", status_code=400)
        if current == new:
            return error_response(
                "Le nouveau mot de passe doit être différent de l'ancien.",
                status_code=400,
            )
        return super().post(request)
