"""MFA-bound account profile shared by Superadmin, Institution and Enterprise.

The already-issued, revocable WebToken is required. Users may update only their
own account metadata and photo, never their role, organisation or permissions.
"""
from django.db import transaction
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import error_response, success_response
from apps.api.v1.core.validators import validate_image_upload
from apps.api.v1.users.web_authentication import EstablishmentWebTokenAuthentication


def _payload(request):
    user = request.user
    return {
        "id": user.pk,
        "full_name": user.get_full_name() or user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "phone_number": user.phone_number or "",
        "photo_url": request.build_absolute_uri(user.photo.url) if user.photo else None,
        "organisation_type": (
            "enterprise" if user.role == "enterprise"
            else "institution" if user.role == "etablissement"
            else "platform"
        ),
    }


class ProfessionalProfileView(APIView):
    authentication_classes = [EstablishmentWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return success_response("Profil professionnel.", _payload(request))

    def patch(self, request):
        user = request.user
        photo = request.FILES.get("photo")
        remove_photo = str(request.data.get("remove_photo", "")).lower() == "true"
        if photo is not None and remove_photo:
            return error_response("Choisissez un ajout ou une suppression de photo.")
        if photo is not None:
            problem = validate_image_upload(photo, "La photo de profil")
            if problem:
                return error_response(problem)
        changes = {}
        for field, max_size in (("first_name", 150), ("last_name", 150), ("phone_number", 20)):
            if field not in request.data:
                continue
            value = request.data.get(field)
            if not isinstance(value, str) or len(value.strip()) > max_size:
                return error_response("Valeur invalide pour " + field + ".")
            changes[field] = value.strip()
        if not (changes or photo or remove_photo):
            return error_response("Aucune modification renseignée.")
        old_photo = user.photo.name if user.photo else ""
        for field, value in changes.items():
            setattr(user, field, value)
        fields = list(changes)
        if photo:
            user.photo = photo
            fields.append("photo")
        elif remove_photo:
            user.photo = None
            fields.append("photo")
        with transaction.atomic():
            user.save(update_fields=fields)
            if old_photo and (photo or remove_photo) and old_photo != (user.photo.name or ""):
                storage = user.photo.storage
                transaction.on_commit(lambda: storage.delete(old_photo))
        log_audit_event("professional_profile_updated", user=user, request=request, metadata={
            "fields": fields, "photo_updated": bool(photo or remove_photo),
        })
        return success_response("Profil professionnel mis à jour.", _payload(request))
