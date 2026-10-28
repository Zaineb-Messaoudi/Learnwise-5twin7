from django.urls import path

from . import consumers

urlpatterns = [
    path('ws/assistant/sessions/<str:session_id>/', consumers.AssistantConsumer.as_asgi()),
]
