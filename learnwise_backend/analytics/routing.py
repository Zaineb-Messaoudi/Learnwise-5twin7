from django.urls import path

from . import consumers

urlpatterns = [
    path('ws/progress/<str:user_id>/', consumers.ProgressConsumer.as_asgi()),
]
