
"""
ASGI config for learnwise_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.
Routes HTTP to Django and WebSocket connections to Channels routing.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnwise_backend.settings")

# Initialize Django before importing routing modules that may access models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from analytics.middleware import QueryStringJWTAuthMiddleware  # noqa: E402
from analytics.routing import websocket_urlpatterns as analytics_websocket_urlpatterns  # noqa: E402
from content.routing import websocket_urlpatterns as content_websocket_urlpatterns  # noqa: E402
from ai_assistant.routing import urlpatterns as assistant_websocket_urlpatterns  # noqa: E402

# Analytics owns the legacy /ws/progress/<id>/ compatibility route.
# Keep analytics routes first to preserve routing precedence.
websocket_urlpatterns = (
    analytics_websocket_urlpatterns
    + content_websocket_urlpatterns
    + assistant_websocket_urlpatterns
)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": QueryStringJWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
