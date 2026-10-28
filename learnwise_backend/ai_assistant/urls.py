from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.AssistantSessionViewSet, basename='assistant-session')
router.register(r'voice-questions', views.VoiceQuestionViewSet, basename='voice-question')
router.register(r'messages', views.AssistantMessageViewSet, basename='assistant-message')
router.register(r'explanations', views.ExplanationViewSet, basename='explanation')
router.register(r'illustrations', views.IllustrationViewSet, basename='illustration')

urlpatterns = [
    path('', include(router.urls)),
]
