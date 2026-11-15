"""
G-Connect - Networking Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Connection, Follow

User = get_user_model()


class NetworkUserSerializer(serializers.ModelSerializer):
    """Représentation minimale d'un utilisateur dans les réponses relations/abonnements."""
    full_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "photo_url", "role"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if getattr(obj, "photo", None):
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None


class ConnectionSerializer(serializers.ModelSerializer):
    requester = NetworkUserSerializer(read_only=True)
    addressee = NetworkUserSerializer(read_only=True)

    class Meta:
        model = Connection
        fields = ["id", "requester", "addressee", "status", "created_at", "responded_at"]
        read_only_fields = fields


class ConnectionCreateSerializer(serializers.Serializer):
    """Payload d'envoi d'une demande de connexion : juste l'id du destinataire."""
    addressee_id = serializers.IntegerField()

    def validate_addressee_id(self, value):
        request = self.context["request"]
        if value == request.user.id:
            raise serializers.ValidationError("Vous ne pouvez pas vous connecter à vous-même.")
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Utilisateur introuvable.")
        if Connection.are_connected(request.user, User.objects.get(id=value)):
            raise serializers.ValidationError("Vous êtes déjà en relation avec cet utilisateur.")
        return value


class FollowSerializer(serializers.ModelSerializer):
    follower = NetworkUserSerializer(read_only=True)
    following = NetworkUserSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "following", "created_at"]
        read_only_fields = fields


class FollowCreateSerializer(serializers.Serializer):
    following_id = serializers.IntegerField()

    def validate_following_id(self, value):
        request = self.context["request"]
        if value == request.user.id:
            raise serializers.ValidationError("Vous ne pouvez pas vous abonner à vous-même.")
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Utilisateur introuvable.")
        return value


class RelationshipStatusSerializer(serializers.Serializer):
    """État de la relation entre l'utilisateur courant et un autre — utilisé
    par le profil pour afficher le bon bouton (Se connecter / En attente /
    Accepter / Relation / Suivre)."""
    connection_status = serializers.ChoiceField(
        choices=["none", "pending_sent", "pending_received", "connected"]
    )
    connection_id = serializers.IntegerField(allow_null=True)
    is_following = serializers.BooleanField()
    mutual_connections_count = serializers.IntegerField()
