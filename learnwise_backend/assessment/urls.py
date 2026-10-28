from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'quizzes', views.QuizViewSet, basename='quiz')
router.register(r'questions', views.QuestionViewSet, basename='question')
router.register(r'choices', views.ChoiceViewSet, basename='choice')
router.register(r'attempts', views.QuizAttemptViewSet, basename='attempt')
router.register(r'answers', views.AnswerViewSet, basename='answer')
router.register(r'evaluations', views.EvaluationViewSet, basename='evaluation')
router.register(r'exercises', views.ExerciseViewSet, basename='exercise')

urlpatterns = [
    path('', include(router.urls)),
    path('generations/', views.QuizGenerationViewSet.as_view({'post': 'create'}), name='quiz-generations'),
    path('generations/<int:pk>/', views.QuizGenerationViewSet.as_view({'get': 'retrieve'}), name='quiz-generation-detail'),
]
