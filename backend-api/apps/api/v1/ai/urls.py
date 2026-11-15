# ai/urls.py
from django.urls import path

from .views import (
    ContentRecommendationsView, HashtagSuggestionView, ImproveWritingView, SummarizeView,
)

urlpatterns = [
    path("hashtags/", HashtagSuggestionView.as_view(), name="ai-hashtags"),
    path("summarize/", SummarizeView.as_view(), name="ai-summarize"),
    path("improve/", ImproveWritingView.as_view(), name="ai-improve"),
    path("recommendations/", ContentRecommendationsView.as_view(), name="ai-recommendations"),
]
