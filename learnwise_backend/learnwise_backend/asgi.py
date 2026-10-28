"""
ASGI config for learnwise_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnwise_backend.settings')

# Django must be fully set up before importing app routing modules that touch models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from analytics.middleware import QueryStringJWTAuthMiddleware  # noqa: E402
from analytics.routing import websocket_urlpatterns as analytics_websocket_urlpatterns  # noqa: E402
from content.routing import websocket_urlpatterns as content_websocket_urlpatterns  # noqa: E402

websocket_urlpatterns = content_websocket_urlpatterns + analytics_websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": QueryStringJWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
})