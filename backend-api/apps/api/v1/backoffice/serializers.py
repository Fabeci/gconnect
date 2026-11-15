# backoffice/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ImportJob, Report

User = get_user_model()


class ImportJobSerializer(serializers.ModelSerializer):
    import_type_display = serializers.CharField(source="get_import_type_display", read_only=True)
    initiated_by_name = serializers.SerializerMethodField()
    institution_name = serializers.CharField(source="institution.name", read_only=True, default=None)

    class Meta:
        model = ImportJob
        fields = [
            "id", "import_type", "import_type_display", "file_name",
            "institution", "institution_name", "initiated_by_name",
            "total_rows", "success_count", "error_count", "errors", "created_rows",
            "created_at",
        ]
        read_only_fields = fields

    def get_initiated_by_name(self, obj):
        if not obj.initiated_by:
            return None
        return obj.initiated_by.get_full_name() or obj.initiated_by.username


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "reported_user", "post", "comment", "reason", "description"]

    def validate(self, attrs):
        targets = [attrs.get("reported_user"), attrs.get("post"), attrs.get("comment")]
        if sum(1 for t in targets if t is not None) != 1:
            raise serializers.ValidationError(
                "Un signalement doit cibler exactement un élément : utilisateur, publication ou commentaire."
            )
        return attrs


class ReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    target_label = serializers.ReadOnlyField()
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "reporter", "reporter_name", "reported_user", "post", "comment",
            "target_label", "reason", "reason_display", "description",
            "status", "status_display", "reviewed_by", "reviewed_by_name",
            "reviewed_at", "created_at",
        ]
        read_only_fields = fields

    def get_reporter_name(self, obj):
        return obj.reporter.get_full_name() or obj.reporter.username

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by:
            return None
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.username


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "role",
            "is_active", "is_banned", "banned_reason", "banned_at", "date_joined",
        ]
        read_only_fields = ["id", "username", "email", "role", "date_joined"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
