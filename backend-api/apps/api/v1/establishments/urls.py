"""
G-Connect - Establishments URLs
Configuration des URLs pour l'application des établissements
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InstitutionViewSet, PromotionViewSet, PromotionMembershipViewSet,
    PromotionJoinRequestViewSet, StudentAccountOrderViewSet,
    SuggestedMembersView, AllMembersView,
)

# Créer le router
router = DefaultRouter()
router.register(r'institutions', InstitutionViewSet, basename='institution')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'memberships', PromotionMembershipViewSet, basename='membership')
router.register(r'join-requests', PromotionJoinRequestViewSet, basename='join-request')
router.register(r'account-orders', StudentAccountOrderViewSet, basename='account-order')

app_name = 'establishments'

urlpatterns = [
    path('', include(router.urls)),
    path('suggestions/', SuggestedMembersView.as_view(), name='suggested-members'),
    path('members/', AllMembersView.as_view(), name='all-members'),
]