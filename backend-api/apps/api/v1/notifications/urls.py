"""
G-Connect - Notifications URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, NotificationPreferenceView, DeviceTokenView

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")

app_name = "notifications"

urlpatterns = [
    path("preferences/", NotificationPreferenceView.as_view(), name="notification-preferences"),
    path("device-token/", DeviceTokenView.as_view(), name="device-token"),
    path("", include(router.urls)),
]
