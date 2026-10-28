from django.urls import path

from .consumers import AnalyticsConsumer, LegacyProgressConsumer

websocket_urlpatterns = [
    path("ws/analytics/", AnalyticsConsumer.as_asgi()),
    path("ws/progress/<str:user_id>/", LegacyProgressConsumer.as_asgi()),
]
