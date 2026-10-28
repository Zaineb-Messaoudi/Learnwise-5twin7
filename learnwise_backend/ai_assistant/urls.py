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
    path('', views.api_root, name='ai-root'),
    path('sessions/', views.SessionListCreateView.as_view(), name='ai-sessions'),
    path(
        'sessions/<int:session_id>/',
        views.SessionDetailView.as_view(),
        name='ai-session-detail',
    ),
    path(
        'sessions/<int:session_id>/messages/',
        views.SessionMessageListCreateView.as_view(),
        name='ai-session-messages',
    ),
    path(
        'sessions/<int:session_id>/voice-questions/',
        views.VoiceQuestionCreateView.as_view(),
        name='ai-voice-question-create',
    ),
    path(
        'voice-questions/<int:question_id>/',
        views.VoiceQuestionDetailView.as_view(),
        name='ai-voice-question-detail',
    ),
    path(
        'messages/<int:message_id>/',
        views.MessageDetailView.as_view(),
        name='ai-message-detail',
    ),
    path(
        'messages/<int:message_id>/explanation/',
        views.MessageExplanationView.as_view(),
        name='ai-message-explanation',
    ),
    path(
        'messages/<int:message_id>/illustrations/',
        views.MessageIllustrationView.as_view(),
        name='ai-message-illustrations',
    ),
    path('', include(router.urls)),
]
