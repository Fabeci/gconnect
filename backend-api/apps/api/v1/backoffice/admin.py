from django.contrib import admin

from .models import ImportJob, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reason', 'status', 'target_label', 'reporter', 'created_at')
    list_filter = ('status', 'reason')
    search_fields = ('reporter__username', 'reporter__email', 'description')
    readonly_fields = ('reporter', 'reported_user', 'post', 'comment', 'created_at')
    ordering = ('-created_at',)


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'import_type', 'file_name', 'institution', 'success_count', 'error_count', 'created_at')
    list_filter = ('import_type',)
    readonly_fields = ('initiated_by', 'institution', 'import_type', 'file_name',
                       'total_rows', 'success_count', 'error_count', 'errors', 'created_rows', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False
