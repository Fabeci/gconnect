# gamification/serializers.py
from rest_framework import serializers

from .models import Badge, UserGamificationProfile, xp_progress


class BadgeSerializer(serializers.ModelSerializer):
    earned = serializers.SerializerMethodField()
    earned_at = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ["id", "code", "name", "description", "icon_emoji", "tier", "xp_reward", "earned", "earned_at"]

    def get_earned(self, obj):
        earned_map = self.context.get("earned_map", {})
        return obj.id in earned_map

    def get_earned_at(self, obj):
        earned_map = self.context.get("earned_map", {})
        entry = earned_map.get(obj.id)
        return entry.earned_at if entry else None


class GamificationProfileSerializer(serializers.Serializer):
    """Pas un ModelSerializer : agrège UserGamificationProfile + les badges
    (obtenus et à débloquer) + le niveau calculé (voir `xp_progress`)."""
    level = serializers.IntegerField()
    xp_total = serializers.IntegerField()
    xp_into_level = serializers.IntegerField()
    xp_for_next_level = serializers.IntegerField()
    badges = BadgeSerializer(many=True)


class LeaderboardEntrySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    full_name = serializers.CharField()
    photo_url = serializers.CharField(allow_null=True)
    total_xp = serializers.IntegerField()
    level = serializers.IntegerField()
