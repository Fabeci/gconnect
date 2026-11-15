"""
G-Connect - Notifications Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.api.v1.establishments.pagination import StandardResultsSetPagination
from .models import Notification, NotificationPreference, DeviceToken
from .serializers import (
    NotificationSerializer, NotificationPreferenceSerializer, DeviceTokenRegisterSerializer,
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET    /notifications/?is_read=false
    DELETE /notifications/{id}/
    POST   /notifications/{id}/mark_read/
    POST   /notifications/mark_all_read/
    GET    /notifications/unread_count/
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).select_related("actor")
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == "true")
        return qs

    def destroy(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.recipient_id != request.user.id:
            return Response({"error": "Vous ne pouvez supprimer que vos propres notifications."},
                             status=status.HTTP_403_FORBIDDEN)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="mark_read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if notification.recipient_id != request.user.id:
            return Response({"error": "Cette notification ne vous appartient pas."},
                             status=status.HTTP_403_FORBIDDEN)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification, context=self.get_serializer_context()).data)

    @action(detail=False, methods=["post"], url_path="mark_all_read")
    def mark_all_read(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"status": "notifications marquées comme lues", "updated": updated})

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})


class NotificationPreferenceView(APIView):
    """
    GET   /notifications/preferences/
    PATCH /notifications/preferences/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pref = NotificationPreference.for_user(request.user)
        return Response(NotificationPreferenceSerializer(pref).data)

    def patch(self, request):
        pref = NotificationPreference.for_user(request.user)
        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DeviceTokenView(APIView):
    """
    POST   /notifications/device-token/   {token, platform} — enregistre
           l'appareil courant pour le push (architecture prête ; aucun envoi
           réel tant qu'aucun fournisseur n'est configuré, voir push.py).
    DELETE /notifications/device-token/   {token} — désinscrit l'appareil
           (déconnexion, changement de compte...).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DeviceToken.register(
            user=request.user,
            token=serializer.validated_data["token"],
            platform=serializer.validated_data["platform"],
        )
        return Response({"status": "appareil enregistré"}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "token requis."}, status=status.HTTP_400_BAD_REQUEST)
        DeviceToken.objects.filter(user=request.user, token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
