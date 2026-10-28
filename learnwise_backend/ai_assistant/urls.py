from django.urls import path

from . import views

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
]
