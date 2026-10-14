"""
Modèles du module `assessment` (module 3 de Learnwise).

Ce module possède : Quiz, Question, Choice, QuizAttempt, Answer, Evaluation,
Exercise, ExerciseChoice, ExerciseSubmission et GenerationJob.
Il ne crée jamais de Course / CourseMaterial : il ne fait que les référencer
(ces modèles appartiennent à l'app `content`).

Choix de conception :
- les identifiants restent des entiers (comme `content.Course`) pour que les
  clés étrangères entre modules restent simples ;
- seul le professeur voit `is_correct` ; les serializers étudiants le cacheront
  (étape 2).
"""
from django.conf import settings
from django.db import models
from django.db.models import Q


# ---------------------------------------------------------------------------
# Listes de valeurs réutilisées par plusieurs modèles
# ---------------------------------------------------------------------------
class Difficulty(models.TextChoices):
    EASY = 'easy', 'Easy'
    MEDIUM = 'medium', 'Medium'
    HARD = 'hard', 'Hard'


class PublishStatus(models.TextChoices):
    # Un contenu généré ou créé reste "draft" jusqu'à la relecture du professeur.
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'


class QuestionType(models.TextChoices):
    SINGLE_CHOICE = 'single_choice', 'Single choice'
    TRUE_FALSE = 'true_false', 'True / False'


# ---------------------------------------------------------------------------
# Quiz, questions et choix
# ---------------------------------------------------------------------------
class Quiz(models.Model):
    # null=True : le contrat demande un cours, mais on tolère les anciennes lignes.
    course = models.ForeignKey(
        'content.Course', on_delete=models.CASCADE,
        related_name='quizzes', null=True, blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=50, choices=Difficulty.choices, default=Difficulty.MEDIUM,
    )
    status = models.CharField(
        max_length=20, choices=PublishStatus.choices, default=PublishStatus.DRAFT,
    )
    # Auteur du quiz (le professeur) ; SET_NULL pour garder le quiz si le compte disparaît.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_quizzes',
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    # `prompt` = l'énoncé (nom utilisé par le contrat frontend).
    prompt = models.TextField()
    type = models.CharField(
        max_length=50, choices=QuestionType.choices, default=QuestionType.SINGLE_CHOICE,
    )
    difficulty = models.CharField(
        max_length=50, choices=Difficulty.choices, default=Difficulty.MEDIUM,
    )
    # Explication montrée à l'étudiant après la soumission (feedback par question).
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Question {self.id} in {self.quiz.title}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    # Indispensable pour corriger : sans ce champ, aucun score n'est calculable.
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Choice for {self.question_id}: {self.text}"


# ---------------------------------------------------------------------------
# Tentatives, réponses et évaluation
# ---------------------------------------------------------------------------
class QuizAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In progress'
        SUBMITTED = 'submitted', 'Submitted'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts',
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        constraints = [
            # Un étudiant n'a qu'UNE tentative "en cours" par quiz
            # (le POST /attempts/ renvoie celle-ci si elle existe).
            # Note : MySQL ignore les contraintes conditionnelles, la vue
            # (étape 3) devra donc aussi faire cette vérification.
            models.UniqueConstraint(
                fields=['user', 'quiz'],
                condition=Q(status='in_progress'),
                name='one_active_attempt_per_user_quiz',
            ),
        ]

    def __str__(self):
        return f"Attempt by {self.user.email} for {self.quiz.title}"


class Answer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    # null = question non répondue (représentée explicitement, comme le demande le contrat).
    selected_choice = models.ForeignKey(
        Choice, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    # Rempli au moment de la soumission, jamais pendant la sauvegarde intermédiaire.
    is_correct = models.BooleanField(default=False)

    class Meta:
        # Une seule réponse par question dans une tentative.
        constraints = [
            models.UniqueConstraint(fields=['attempt', 'question'], name='one_answer_per_question'),
        ]

    def __str__(self):
        return f"Answer for {self.question_id} in attempt {self.attempt_id}"


class Evaluation(models.Model):
    # OneToOne : une tentative soumise a exactement une évaluation.
    attempt = models.OneToOneField(
        QuizAttempt, on_delete=models.CASCADE, related_name='evaluation',
    )
    # Le contrat demande des COMPTES, pas des pourcentages.
    score = models.FloatField()
    correct_answers = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    feedback = models.TextField(blank=True)
    # Liste de {question_id, question, is_correct, feedback}.
    question_feedback = models.JSONField(default=list, blank=True)
    # Prochaines étapes suggérées à l'étudiant.
    next_steps = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"Evaluation for attempt {self.attempt_id}"


# ---------------------------------------------------------------------------
# Exercices (endpoints indépendants des quiz dans le contrat)
# ---------------------------------------------------------------------------
class Exercise(models.Model):
    course = models.ForeignKey(
        'content.Course', on_delete=models.CASCADE,
        related_name='exercises', null=True, blank=True,
    )
    # Lien optionnel : un exercice peut exister sans quiz.
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='exercises', null=True, blank=True,
    )
    title = models.CharField(max_length=255, default='')
    description = models.TextField(blank=True, default='')
    prompt = models.TextField()
    # Feedback montré après la soumission.
    explanation = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20, choices=PublishStatus.choices, default=PublishStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_exercises',
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.title or f"Exercise {self.id}"


class ExerciseChoice(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Choice for exercise {self.exercise_id}: {self.text}"


class ExerciseSubmission(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exercise_submissions',
    )
    selected_choice = models.ForeignKey(
        ExerciseChoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Submission of {self.user_id} for exercise {self.exercise_id}"


# ---------------------------------------------------------------------------
# Génération IA (Gemini) : tâche suivie par l'endpoint /generations/{id}/
# ---------------------------------------------------------------------------
class GenerationJob(models.Model):
    class Kind(models.TextChoices):
        QUIZ = 'quiz', 'Quiz'
        EXERCISE = 'exercise', 'Exercise'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generation_jobs',
    )
    course = models.ForeignKey(
        'content.Course', on_delete=models.CASCADE,
        related_name='generation_jobs', null=True, blank=True,
    )
    # Paramètres de la demande, tels que le contrat les définit.
    material_ids = models.JSONField(default=list, blank=True)
    source_text = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.QUIZ)
    question_count = models.PositiveIntegerField(default=5)
    difficulty = models.CharField(
        max_length=50, choices=Difficulty.choices, default=Difficulty.MEDIUM,
    )
    # Suivi du traitement (le front fait du polling sur ce statut).
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    error_message = models.TextField(blank=True)
    # Brouillon créé à la fin de la génération (relu puis publié par le professeur).
    quiz = models.ForeignKey(Quiz, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    exercise = models.ForeignKey(Exercise, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Generation {self.id} ({self.kind}, {self.status})"