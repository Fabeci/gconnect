# publicapi/serializers.py
from rest_framework import serializers

from .models import ApiKey, WebhookSubscription


class ApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiKey
        fields = ["id", "name", "key_prefix", "is_active", "created_at", "last_used_at"]
        read_only_fields = fields


class ApiKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    event_display = serializers.CharField(source="get_event_display", read_only=True)

    class Meta:
        model = WebhookSubscription
        fields = [
            "id", "target_url", "event", "event_display", "secret", "is_active",
            "created_at", "last_triggered_at", "last_status_code",
        ]
        read_only_fields = ["id", "secret", "created_at", "last_triggered_at", "last_status_code"]

    def validate_event(self, value):
        if value not in WebhookSubscription.Event.values:
            raise serializers.ValidationError("Type d'événement inconnu.")
        return value
