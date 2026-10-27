from django.urls import path
from .consumers import AnalyticsConsumer

websocket_urlpatterns = [path("ws/analytics/", AnalyticsConsumer.as_asgi())]
