"""
G-Connect - Messaging URLs
Configuration des URLs pour l'application de messagerie
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet, TypingIndicatorViewSet

# Créer le router
router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'typing', TypingIndicatorViewSet, basename='typing')

app_name = 'messaging'

urlpatterns = [
    path('', include(router.urls)),
]