from django.contrib import admin
from .models import Connection, Follow


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ("id", "requester", "addressee", "status", "created_at", "responded_at")
    list_filter = ("status",)
    search_fields = ("requester__username", "addressee__username")
    autocomplete_fields = ("requester", "addressee")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")
    autocomplete_fields = ("follower", "following")
