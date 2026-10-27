from django.urls import path
from content import consumers

websocket_urlpatterns = [
    path('ws/content/courses/<int:course_id>/presence/', consumers.PresenceConsumer.as_asgi()),
]
