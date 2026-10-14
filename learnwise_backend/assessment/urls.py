"""
Routes du module `assessment`, montées sous /api/v1/assessment/ par le projet.
Elles suivent exactement le tableau du fichier docs/frontend-backend-contract.md.

Étapes 2, 3 et 5 : quiz, tentatives et exercices sont réels ; la génération IA
pointe encore vers NotImplementedView (501).
"""
from django.urls import path

from . import views

# Raccourci : même vue provisoire pour toutes les routes.
todo = views.NotImplementedView.as_view()

urlpatterns = [
    path('', views.api_root, name='assessment-root'),

    # --- Quiz ---
    path('quizzes/', views.QuizListCreateView.as_view(), name='quiz-list'),                                    # GET liste, POST création
    path('quizzes/<int:quiz_id>/', views.QuizDetailView.as_view(), name='quiz-detail'),                    # GET, PATCH, DELETE
    path('quizzes/<int:quiz_id>/publish/', views.QuizPublishView.as_view(), name='quiz-publish'),           # POST publier

    # --- Tentatives d'un quiz ---
    path('quizzes/<int:quiz_id>/attempts/', views.AttemptListCreateView.as_view(), name='attempt-list'),          # GET liste, POST démarrer
    path('quizzes/<int:quiz_id>/attempts/<int:attempt_id>/', views.AttemptDetailView.as_view(), name='attempt-detail'),             # PATCH sauvegarder les réponses
    path('quizzes/<int:quiz_id>/attempts/<int:attempt_id>/submit/', views.AttemptSubmitView.as_view(), name='attempt-submit'),      # POST soumettre
    path('quizzes/<int:quiz_id>/attempts/<int:attempt_id>/evaluation/', views.AttemptEvaluationView.as_view(), name='attempt-evaluation'),  # GET résultat

    # --- Génération IA (Gemini) ---
    path('generations/', todo, name='generation-create'),                        # POST lancer une génération
    path('generations/<int:generation_id>/', todo, name='generation-detail'),    # GET suivre l'état (polling)

    # --- Exercices ---
    path('exercises/', views.ExerciseListCreateView.as_view(), name='exercise-list'),                              # GET liste, POST création
    path('exercises/<int:exercise_id>/', views.ExerciseDetailView.as_view(), name='exercise-detail'),          # GET, PATCH, DELETE
    path('exercises/<int:exercise_id>/publish/', views.ExercisePublishView.as_view(), name='exercise-publish'), # POST publier
    path('exercises/<int:exercise_id>/submissions/', views.ExerciseSubmissionView.as_view(), name='exercise-submissions'),  # POST répondre
]