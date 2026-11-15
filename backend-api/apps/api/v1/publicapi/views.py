# publicapi/views.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.core.responses import success_response

from .models import ApiKey, WebhookSubscription
from .serializers import ApiKeyCreateSerializer, ApiKeySerializer, WebhookSubscriptionSerializer


class ApiKeyViewSet(viewsets.ModelViewSet):
    """
    GET    /publicapi/keys/         — mes clés API (jamais le secret en clair).
    POST   /publicapi/keys/         {name} → {..., "key": "gck_..."} (une seule fois).
    DELETE /publicapi/keys/{id}/    — révoque la clé.
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return ApiKey.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return ApiKeyCreateSerializer if self.action == "create" else ApiKeySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance, raw_key = ApiKey.generate(request.user, serializer.validated_data["name"])
        log_audit_event("api_key_created", user=request.user, request=request, metadata={"name": instance.name})
        data = {**ApiKeySerializer(instance).data, "key": raw_key}
        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        log_audit_event("api_key_revoked", user=request.user, request=request, metadata={"name": instance.name})
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebhookSubscriptionViewSet(viewsets.ModelViewSet):
    """CRUD des abonnements webhook de l'utilisateur connecté."""
    permission_classes = [IsAuthenticated]
    serializer_class = WebhookSubscriptionSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return WebhookSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
