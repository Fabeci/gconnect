# publicapi/urls.py
from rest_framework.routers import DefaultRouter

from .views import ApiKeyViewSet, WebhookSubscriptionViewSet

router = DefaultRouter()
router.register(r"keys", ApiKeyViewSet, basename="api-key")
router.register(r"webhooks", WebhookSubscriptionViewSet, basename="webhook")

urlpatterns = router.urls
