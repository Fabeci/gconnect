from rest_framework import serializers

from apps.api.v1.core.models import Interest, Preference, Sector, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['id', 'name']


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = ['id', 'name']


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ['id', 'name']