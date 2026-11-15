from django.contrib import admin

from .models import Badge, UserBadge, UserGamificationProfile, XPEvent


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('icon_emoji', 'name', 'code', 'tier', 'xp_reward')
    list_filter = ('tier',)


@admin.register(UserGamificationProfile)
class UserGamificationProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_xp', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'total_xp', 'updated_at')

    def has_add_permission(self, request):
        return False


@admin.register(XPEvent)
class XPEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'reason', 'created_at')
    list_filter = ('reason',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'amount', 'reason', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'badge', 'earned_at')

    def has_add_permission(self, request):
        return False
