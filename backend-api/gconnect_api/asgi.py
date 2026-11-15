"""
ASGI config for gconnect_api project.
Gère les connexions HTTP (Django) et WebSocket (Django Channels).
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gconnect_api.settings.dev')

django_asgi_app = get_asgi_application()

from apps.api.v1.messaging.routing import websocket_urlpatterns  # noqa: E402
from apps.api.v1.messaging.middleware import TokenAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        TokenAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
