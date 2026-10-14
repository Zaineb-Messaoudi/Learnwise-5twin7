"""
Serializers du module `assessment` (étape 2 : quiz).

Deux représentations en lecture :
- professeur : voit `is_correct` et `explanation` (pour relire le quiz) ;
- étudiant   : ne voit JAMAIS `is_correct` (sinon il lirait les réponses).
Un serializer d'écriture unique valide ce que le professeur envoie.

Le contrat demande des identifiants "opaques" de type chaîne : on renvoie
donc tous les ids en texte ("12" et non 12).
"""
from django.db import transaction
from rest_framework import serializers

from content.models import Course

from .models import Choice, Difficulty, Question, QuestionType, Quiz


# ---------------------------------------------------------------------------
# Lecture : choix et questions
# ---------------------------------------------------------------------------
class ChoiceStudentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)  # id renvoyé en chaîne

    class Meta:
        model = Choice
        fields = ['id', 'text']  # pas de is_correct côté étudiant


class ChoiceTeacherSerializer(ChoiceStudentSerializer):
    class Meta(ChoiceStudentSerializer.Meta):
        fields = ['id', 'text', 'is_correct']


class QuestionStudentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    choices = ChoiceStudentSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'prompt', 'type', 'choices']


class QuestionTeacherSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    choices = ChoiceTeacherSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'prompt', 'type', 'difficulty', 'explanation', 'choices']


# ---------------------------------------------------------------------------
# Lecture : quiz (liste, détail étudiant, détail professeur)
# ---------------------------------------------------------------------------
class QuizListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    course_id = serializers.SerializerMethodField()
    author_id = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'course_id', 'title', 'description', 'difficulty', 'status',
            'question_count', 'author_id', 'created_at', 'updated_at', 'published_at',
        ]

    def get_course_id(self, obj):
        return str(obj.course_id) if obj.course_id else None

    def get_author_id(self, obj):
        return str(obj.created_by_id) if obj.created_by_id else None

    def get_question_count(self, obj):
        # len() sur .all() réutilise le prefetch : pas de requête SQL en plus.
        return len(obj.questions.all())


def _scoring_rules(quiz):
    """Règles de notation renvoyées avec le quiz (le contrat l'exige)."""
    total = len(quiz.questions.all())
    return {
        'type': 'count',                 # le score est un nombre de bonnes réponses
        'points_per_question': 1,
        'max_score': total,
        'negative_marking': False,       # une mauvaise réponse ne retire rien
        'unanswered_counts_as': 'incorrect',
    }


class QuizDetailStudentSerializer(QuizListSerializer):
    questions = QuestionStudentSerializer(many=True, read_only=True)
    scoring = serializers.SerializerMethodField()

    class Meta(QuizListSerializer.Meta):
        fields = QuizListSerializer.Meta.fields + ['questions', 'scoring']

    def get_scoring(self, obj):
        return _scoring_rules(obj)


class QuizDetailTeacherSerializer(QuizDetailStudentSerializer):
    questions = QuestionTeacherSerializer(many=True, read_only=True)


# ---------------------------------------------------------------------------
# Écriture : ce que le professeur envoie (création et modification)
# ---------------------------------------------------------------------------
class ChoiceInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=255)
    is_correct = serializers.BooleanField(default=False)


class QuestionInputSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    type = serializers.ChoiceField(choices=QuestionType.choices, default=QuestionType.SINGLE_CHOICE)
    difficulty = serializers.ChoiceField(choices=Difficulty.choices, default=Difficulty.MEDIUM)
    explanation = serializers.CharField(required=False, allow_blank=True, default='')
    # Un brouillon peut être incomplet : on exige les choix seulement à la publication.
    choices = ChoiceInputSerializer(many=True, required=False)


def _save_questions(quiz, questions):
    """Crée les questions et leurs choix ; l'ordre de la liste devient `order`."""
    for position, data in enumerate(questions):
        choices = data.pop('choices', [])
        question = Question.objects.create(quiz=quiz, order=position, **data)
        Choice.objects.bulk_create([
            Choice(question=question, order=index, **choice)
            for index, choice in enumerate(choices)
        ])


class QuizWriteSerializer(serializers.ModelSerializer):
    # Le contrat parle de `course_id` ; on le relie au champ `course` du modèle.
    course_id = serializers.PrimaryKeyRelatedField(
        source='course', queryset=Course.objects.all(),
    )
    questions = QuestionInputSerializer(many=True, required=False)

    class Meta:
        model = Quiz
        fields = ['course_id', 'title', 'description', 'difficulty', 'questions']

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop('questions', [])
        # L'auteur est toujours l'utilisateur connecté, jamais une valeur envoyée.
        quiz = Quiz.objects.create(created_by=self.context['request'].user, **validated_data)
        _save_questions(quiz, questions)
        return quiz

    @transaction.atomic
    def update(self, instance, validated_data):
        questions = validated_data.pop('questions', None)
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        # Si `questions` est envoyé, il REMPLACE toute la liste (le quiz est
        # un brouillon, donc aucune tentative d'étudiant n'en dépend).
        if questions is not None:
            instance.questions.all().delete()
            _save_questions(instance, questions)
        return instance


# ---------------------------------------------------------------------------
# Publication : un quiz doit être complet avant d'être visible des étudiants
# ---------------------------------------------------------------------------
def publish_errors(quiz):
    """Renvoie la liste des problèmes qui empêchent la publication (vide = prêt)."""
    questions = list(quiz.questions.all())
    if not questions:
        return ['A quiz needs at least one question to be published.']
    errors = []
    for number, question in enumerate(questions, start=1):
        choices = list(question.choices.all())
        correct = [choice for choice in choices if choice.is_correct]
        if len(choices) < 2:
            errors.append(f'Question {number} needs at least 2 choices.')
        if len(correct) != 1:
            errors.append(f'Question {number} needs exactly 1 correct choice.')
    return errors