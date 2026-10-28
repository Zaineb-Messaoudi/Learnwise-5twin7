from django.urls import path
from content import consumers

websocket_urlpatterns = [
    path('ws/content/courses/<int:course_id>/presence/', consumers.PresenceConsumer.as_asgi()),
    path('ws/progress/<str:user_id>/', consumers.ProgressConsumer.as_asgi()),
    path('ws/assistant/sessions/<str:session_id>/', consumers.AssistantConsumer.as_asgi()),
    path('ws/analytics/', consumers.AnalyticsConsumer.as_asgi()),
]
