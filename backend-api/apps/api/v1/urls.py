from django.urls import path, include
from apps.api.v1.users.views import GlobalSearchView

urlpatterns = [
    path('users/', include('apps.api.v1.users.urls')),
    path('establishments/', include('apps.api.v1.establishments.urls')),
    path('posts/', include('apps.api.v1.posts.urls')),
    path('messaging/', include('apps.api.v1.messaging.urls')),
    path('networking/', include('apps.api.v1.networking.urls')),
    path('notifications/', include('apps.api.v1.notifications.urls')),
    path('backoffice/', include('apps.api.v1.backoffice.urls')),
    path('subscriptions/', include('apps.api.v1.subscriptions.urls')),
    path('gamification/', include('apps.api.v1.gamification.urls')),
    path('ai/', include('apps.api.v1.ai.urls')),
    path('public/', include('apps.api.v1.publicapi.urls')),
    path('search/', GlobalSearchView.as_view(), name='global-search'),
]

