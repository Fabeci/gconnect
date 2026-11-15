"""
G-Connect - Networking URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConnectionViewSet, FollowViewSet, RelationshipStatusView, ConnectionSuggestionsView,
)

router = DefaultRouter()
router.register(r"connections", ConnectionViewSet, basename="connection")
router.register(r"follows", FollowViewSet, basename="follow")

app_name = "networking"

urlpatterns = [
    path("", include(router.urls)),
    path("status/<int:user_id>/", RelationshipStatusView.as_view(), name="relationship-status"),
    path("suggestions/", ConnectionSuggestionsView.as_view(), name="connection-suggestions"),
]
