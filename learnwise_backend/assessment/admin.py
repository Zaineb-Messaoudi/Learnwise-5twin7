"""
Enregistrement des modèles dans l'admin Django (http://localhost:8000/admin/).
Pratique pour créer des quiz de test à la main avant que l'API soit terminée.
"""
from django.contrib import admin

from .models import (
    Answer, Choice, Evaluation, Exercise, ExerciseChoice, ExerciseSubmission,
    GenerationJob, Question, Quiz, QuizAttempt,
)


# Django n'accepte pas les inlines imbriqués : on ajoute les questions dans le quiz,
# et les choix dans la question.
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('order', 'prompt', 'type', 'difficulty')
    show_change_link = True  # lien vers la page de la question pour éditer ses choix


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2
    fields = ('order', 'text', 'is_correct')


class ExerciseChoiceInline(admin.TabularInline):
    model = ExerciseChoice
    extra = 2
    fields = ('order', 'text', 'is_correct')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'difficulty', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'difficulty')
    search_fields = ('title', 'description')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'quiz', 'prompt', 'type', 'order')
    list_filter = ('type', 'difficulty')
    search_fields = ('prompt',)
    inlines = [ChoiceInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'quiz', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'prompt')
    inlines = [ExerciseChoiceInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'quiz', 'status', 'started_at', 'submitted_at')
    list_filter = ('status',)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'attempt', 'question', 'selected_choice', 'is_correct')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'attempt', 'score', 'correct_answers', 'total_questions', 'created_at')


@admin.register(ExerciseSubmission)
class ExerciseSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'exercise', 'user', 'is_correct', 'submitted_at')


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'status', 'requested_by', 'course', 'created_at')
    list_filter = ('kind', 'status')