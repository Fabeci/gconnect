from django.contrib import admin

from .models import ApiKey, WebhookSubscription


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'key_prefix', 'user', 'is_active', 'created_at', 'last_used_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('user', 'name', 'key_hash', 'key_prefix', 'created_at', 'last_used_at')

    def has_add_permission(self, request):
        return False


@admin.register(WebhookSubscription)
class WebhookSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('event', 'target_url', 'user', 'is_active', 'last_triggered_at', 'last_status_code')
    list_filter = ('event', 'is_active')
    search_fields = ('target_url', 'user__username', 'user__email')
    readonly_fields = ('user', 'secret', 'created_at', 'last_triggered_at', 'last_status_code')
