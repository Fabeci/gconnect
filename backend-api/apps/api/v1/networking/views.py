"""
G-Connect - Networking Views
Demandes de connexion (bidirectionnelles) et abonnements (follow, asymétriques).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.api.v1.establishments.pagination import StandardResultsSetPagination
from .models import Connection, Follow
from .serializers import (
    ConnectionSerializer, ConnectionCreateSerializer,
    FollowSerializer, FollowCreateSerializer,
    RelationshipStatusSerializer, NetworkUserSerializer,
)
from .suggestions import build_connection_suggestions

User = get_user_model()


class ConnectionViewSet(viewsets.ModelViewSet):
    """
    GET    /networking/connections/?box=received|sent&status=pending
    POST   /networking/connections/                {addressee_id}
    POST   /networking/connections/{id}/accept/
    POST   /networking/connections/{id}/decline/
    DELETE /networking/connections/{id}/            (annule si en attente, supprime la relation si acceptée)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = ConnectionSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Connection.objects.filter(Q(requester=user) | Q(addressee=user)).select_related(
            "requester", "addressee"
        )

        box = self.request.query_params.get("box")
        if box == "received":
            qs = qs.filter(addressee=user)
        elif box == "sent":
            qs = qs.filter(requester=user)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = ConnectionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        addressee = User.objects.get(id=serializer.validated_data["addressee_id"])

        # Demande croisée déjà en attente dans l'autre sens → on l'accepte
        # directement plutôt que de créer une seconde ligne en double.
        reverse_pending = Connection.objects.filter(
            requester=addressee, addressee=request.user, status=Connection.Status.PENDING
        ).first()
        if reverse_pending:
            reverse_pending.accept()
            detail = ConnectionSerializer(reverse_pending, context=self.get_serializer_context())
            return Response(detail.data, status=status.HTTP_200_OK)

        existing = Connection.objects.filter(requester=request.user, addressee=addressee).first()
        if existing:
            if existing.status == Connection.Status.DECLINED:
                existing.status = Connection.Status.PENDING
                existing.responded_at = None
                existing.save(update_fields=["status", "responded_at"])
            detail = ConnectionSerializer(existing, context=self.get_serializer_context())
            return Response(detail.data, status=status.HTTP_200_OK)

        connection = Connection.objects.create(requester=request.user, addressee=addressee)
        detail = ConnectionSerializer(connection, context=self.get_serializer_context())
        return Response(detail.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        connection = self.get_object()
        if request.user not in (connection.requester, connection.addressee):
            return Response({"error": "Vous ne faites pas partie de cette relation."},
                             status=status.HTTP_403_FORBIDDEN)
        connection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        connection = self.get_object()
        if connection.addressee_id != request.user.id:
            return Response({"error": "Seul le destinataire peut accepter cette demande."},
                             status=status.HTTP_403_FORBIDDEN)
        if connection.status != Connection.Status.PENDING:
            return Response({"error": "Cette demande n'est plus en attente."}, status=status.HTTP_400_BAD_REQUEST)
        connection.accept()
        return Response(ConnectionSerializer(connection, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        connection = self.get_object()
        if connection.addressee_id != request.user.id:
            return Response({"error": "Seul le destinataire peut refuser cette demande."},
                             status=status.HTTP_403_FORBIDDEN)
        if connection.status != Connection.Status.PENDING:
            return Response({"error": "Cette demande n'est plus en attente."}, status=status.HTTP_400_BAD_REQUEST)
        connection.decline()
        return Response(ConnectionSerializer(connection, context=self.get_serializer_context()).data)

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        """Liste des utilisateurs avec qui je suis effectivement connecté (statut accepté)."""
        ids = Connection.connected_ids(request.user)
        connected_qs = User.objects.filter(id__in=ids).order_by("first_name", "last_name", "id")
        page = self.paginate_queryset(connected_qs)
        target = page if page is not None else connected_qs
        serializer = NetworkUserSerializer(target, many=True, context=self.get_serializer_context())
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class FollowViewSet(viewsets.ModelViewSet):
    """
    GET    /networking/follows/?box=followers|following&user=<id>
    POST   /networking/follows/                 {following_id}
    DELETE /networking/follows/{id}/
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = FollowSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get("user")
        box = self.request.query_params.get("box", "following")

        if user_id:
            target_user_id = user_id
        else:
            target_user_id = self.request.user.id

        qs = Follow.objects.select_related("follower", "following")
        if box == "followers":
            qs = qs.filter(following_id=target_user_id)
        else:
            qs = qs.filter(follower_id=target_user_id)
        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = FollowCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        following_user = User.objects.get(id=serializer.validated_data["following_id"])

        follow, created = Follow.objects.get_or_create(follower=request.user, following=following_user)
        detail = FollowSerializer(follow, context=self.get_serializer_context())
        return Response(detail.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        follow = self.get_object()
        if follow.follower_id != request.user.id:
            return Response({"error": "Vous ne pouvez retirer que vos propres abonnements."},
                             status=status.HTTP_403_FORBIDDEN)
        follow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="unfollow")
    def unfollow(self, request):
        """Alternative pratique à DELETE /follows/{id}/ quand le client n'a que l'id de l'utilisateur suivi."""
        following_id = request.data.get("following_id")
        deleted, _ = Follow.objects.filter(follower=request.user, following_id=following_id).delete()
        if deleted:
            return Response({"status": "désabonné"})
        return Response({"error": "Abonnement introuvable."}, status=status.HTTP_404_NOT_FOUND)


class RelationshipStatusView(APIView):
    """GET /networking/status/{user_id}/ — état de la relation avec un utilisateur donné."""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        other = get_object_or_404(User, id=user_id)
        me = request.user

        connection_status = "none"
        connection_id = None

        if me.id != other.id:
            connection = Connection.objects.filter(
                Q(requester=me, addressee=other) | Q(requester=other, addressee=me)
            ).first()
            if connection:
                connection_id = connection.id
                if connection.status == Connection.Status.ACCEPTED:
                    connection_status = "connected"
                elif connection.status == Connection.Status.PENDING:
                    connection_status = "pending_sent" if connection.requester_id == me.id else "pending_received"

        is_following = Follow.objects.filter(follower=me, following=other).exists()

        mutual_count = 0
        if me.id != other.id:
            mutual_count = len(Connection.connected_ids(me) & Connection.connected_ids(other))

        data = RelationshipStatusSerializer({
            "connection_status": connection_status,
            "connection_id": connection_id,
            "is_following": is_following,
            "mutual_connections_count": mutual_count,
        }).data
        return Response(data)


class ConnectionSuggestionsView(APIView):
    """GET /networking/suggestions/?limit=10 — personnes à connaître,
    classées par pertinence (établissement, promotion, relations communes,
    centres d'intérêt). Chaque résultat inclut un breakdown filtrable
    (same_institution/same_promotion/mutual_count) et jusqu'à 3 relations
    mutuelles réelles (avec photo) pour l'onglet "Découvrir" du réseau."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 10)), 50)
        except ValueError:
            limit = 10

        scored = build_connection_suggestions(request.user, limit=limit)
        context = {"request": request}

        # Aperçus des relations mutuelles — 1 requête groupée pour tous les
        # candidats plutôt qu'une requête par candidat.
        preview_ids = {pid for _, _, _, b in scored for pid in b.get("mutual_preview_ids", [])}
        preview_users = User.objects.in_bulk(preview_ids) if preview_ids else {}

        results = []
        for score, candidate, reason, breakdown in scored:
            previews = []
            for pid in breakdown.get("mutual_preview_ids", []):
                pu = preview_users.get(pid)
                if pu:
                    previews.append(NetworkUserSerializer(pu, context=context).data)
            results.append({
                "user": NetworkUserSerializer(candidate, context=context).data,
                "score": score,
                "reason": reason,
                "same_institution": breakdown.get("same_institution", False),
                "same_promotion": breakdown.get("same_promotion", False),
                "mutual_connections_count": breakdown.get("mutual_count", 0),
                "mutual_connections_preview": previews,
            })
        return Response({"count": len(results), "results": results})
