"""
ASGI config for learnwise_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnwise_backend.settings')

# Django must be fully set up before importing app routing modules that touch models.
django_app = get_asgi_application()
from content.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
