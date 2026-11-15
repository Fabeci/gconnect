from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied, NotAuthenticated


def success_response(message, data=None, status_code=200):
    return Response({
        "success": True,
        "message": message,
        "status": status_code,
        "data": data
    }, status=status_code)

def error_response(message, errors=None, status_code=400):
    return Response({
        "success": False,
        "message": message,
        "status": status_code,
        "errors": errors
    }, status=status_code)


def custom_exception_handler(exc, context):
    # Utilise le handler par défaut
    response = exception_handler(exc, context)

    if isinstance(exc, PermissionDenied):
        return error_response(
            message="Accès refusé : vous n'avez pas la permission d'effectuer cette action.",
            errors={"detail": str(exc)},
            status_code=403
        )

    elif isinstance(exc, NotAuthenticated):
        return error_response(
            message="Authentification requise.",
            errors={"detail": str(exc)},
            status_code=401
        )

    # Autres erreurs par défaut
    return response
