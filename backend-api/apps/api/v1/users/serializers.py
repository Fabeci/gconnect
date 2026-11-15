from rest_framework import serializers

from apps.api.v1.core.models import Interest, Preference, Sector, Skill
from apps.api.v1.core.serializers import InterestSerializer, PreferenceSerializer, SectorSerializer, SkillSerializer
from apps.api.v1.users.models import Alumni, InstitutionAdmin, Student, User, ProfilePrivacy

class StudentSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email')
    username = serializers.CharField(source='user.username')
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)

    student_id = serializers.CharField()
    gender = serializers.CharField()
    date_of_birth = serializers.DateField()
    skills = SkillSerializer(many=True, read_only=True)
    interests = InterestSerializer(many=True, read_only=True)
    preferences = PreferenceSerializer(many=True, read_only=True)
    sectors = SectorSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'gender', 'date_of_birth', 'student_id', 'date_joined',
            'skills', 'interests', 'preferences', 'sectors'
        ]

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class AlumniSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    interests = InterestSerializer(many=True, read_only=True)
    preferences = PreferenceSerializer(many=True, read_only=True)
    sectors = SectorSerializer(many=True, read_only=True)

    class Meta:
        model = Alumni
        fields = [
            'id', 'gender', 'graduation_date', 'institution', 'promotion',
            'skills', 'interests', 'preferences', 'sectors', 'proof_document'
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'date_joined', 'last_login', 'photo']


class InstitutionAdminSerializer(serializers.ModelSerializer):
    user = UserSerializer()  # ou serializers.StringRelatedField() selon le niveau de détail

    class Meta:
        model = InstitutionAdmin
        fields = ['id', 'user', 'institution']


class ProfilePrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfilePrivacy
        fields = [
            'profile_visibility', 'photo_visibility', 'cover_visibility',
            'phone_visibility', 'email_visibility', 'experience_visibility',
            'cv_visibility', 'skills_visibility', 'posts_visibility',
        ]