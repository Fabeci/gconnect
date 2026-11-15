# gamification/views.py
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.v1.core.responses import success_response
from apps.api.v1.establishments.pagination import StandardResultsSetPagination

from .models import Badge, UserBadge, UserGamificationProfile, xp_progress
from .serializers import BadgeSerializer, LeaderboardEntrySerializer
from .services import member_of_the_month

User = get_user_model()


class GamificationProfileView(APIView):
    """GET /gamification/me/ — XP, niveau, badges obtenus et à débloquer."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserGamificationProfile.for_user(request.user)
        progress = xp_progress(profile.total_xp)

        earned = list(UserBadge.objects.filter(user=request.user).select_related("badge"))
        earned_map = {ub.badge_id: ub for ub in earned}

        badges = Badge.objects.all().order_by("tier", "name")
        badge_data = BadgeSerializer(badges, many=True, context={"earned_map": earned_map}).data

        data = {**progress, "badges": badge_data}
        return success_response("Profil de gamification.", data)


class LeaderboardView(APIView):
    """GET /gamification/leaderboard/?page=&page_size= — classement par XP total."""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        qs = UserGamificationProfile.objects.select_related("user").filter(
            total_xp__gt=0
        ).order_by("-total_xp", "user_id")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        target = page if page is not None else qs

        data = [
            {
                "user_id": p.user_id,
                "full_name": p.user.get_full_name() or p.user.username,
                "photo_url": request.build_absolute_uri(p.user.photo.url) if p.user.photo else None,
                "total_xp": p.total_xp,
                "level": xp_progress(p.total_xp)["level"],
            }
            for p in target
        ]
        serialized = LeaderboardEntrySerializer(data, many=True).data

        if page is not None:
            return paginator.get_paginated_response(serialized)
        return success_response("Classement.", serialized)


class MemberOfTheMonthView(APIView):
    """GET /gamification/member-of-the-month/ — calculé à la demande
    (aucune tâche planifiée dans ce projet — voir note dans services.py)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user, month_xp = member_of_the_month()
        if not user:
            return success_response("Aucun membre du mois pour l'instant.", None)

        data = {
            "user_id": user.id,
            "full_name": user.get_full_name() or user.username,
            "photo_url": request.build_absolute_uri(user.photo.url) if user.photo else None,
            "month_xp": month_xp,
        }
        return success_response("Membre du mois.", data)
