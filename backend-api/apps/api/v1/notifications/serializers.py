"""
G-Connect - Notifications Serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Notification, NotificationPreference, DeviceToken

User = get_user_model()


class NotificationActorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "photo_url"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if getattr(obj, "photo", None):
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None


class NotificationSerializer(serializers.ModelSerializer):
    actor = NotificationActorSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "actor", "notification_type", "verb",
            "target_type", "target_id", "is_read", "created_at",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "push_enabled", "email_enabled", "connections_enabled",
            "messages_enabled", "reactions_enabled", "comments_enabled",
        ]


class DeviceTokenRegisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices, default=DeviceToken.Platform.ANDROID)
