# gamification/urls.py
from django.urls import path

from .views import GamificationProfileView, LeaderboardView, MemberOfTheMonthView

urlpatterns = [
    path("me/", GamificationProfileView.as_view(), name="gamification-me"),
    path("leaderboard/", LeaderboardView.as_view(), name="gamification-leaderboard"),
    path("member-of-the-month/", MemberOfTheMonthView.as_view(), name="gamification-motm"),
]
