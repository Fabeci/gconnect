from django.contrib import admin
from .models import Notification, NotificationPreference, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "actor", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("recipient__username", "actor__username")
    autocomplete_fields = ("recipient", "actor")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "push_enabled", "email_enabled", "connections_enabled", "messages_enabled",
                     "reactions_enabled", "comments_enabled")
    autocomplete_fields = ("user",)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "platform", "created_at", "last_seen_at")
    list_filter = ("platform",)
    search_fields = ("user__username", "token")
    autocomplete_fields = ("user",)
