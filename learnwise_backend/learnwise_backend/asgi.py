"""
ASGI config for learnwise_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.
Routes HTTP to Django's WSGI/ASGI app and WebSocket to Channels routing.
"""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnwise_backend.settings')

django.setup()

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from ai_assistant.routing import urlpatterns as assistant_websocket_urls
from analytics.routing import urlpatterns as analytics_websocket_urls

django_application = get_asgi_application()

websocket_urlpatterns = [
    *assistant_websocket_urls,
    *analytics_websocket_urls,
]

application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
