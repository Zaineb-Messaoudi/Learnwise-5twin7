"""
Serializers du module `assessment` (étape 2 : quiz, étape 3 : tentatives, étape 5 : exercices).

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

from .models import (
    Answer, Choice, Difficulty, Evaluation, Exercise, ExerciseChoice, ExerciseSubmission,
    Question, QuestionType, Quiz, QuizAttempt,
)
from .permissions import is_admin


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


# ---------------------------------------------------------------------------
# Étape 3 : tentatives, réponses et évaluation
# ---------------------------------------------------------------------------
class AttemptSerializer(serializers.ModelSerializer):
    """
    Une tentative avec sa "answer map" : {id_question: id_choix}.
    Les questions sans réponse figurent explicitement avec la valeur null
    (c'est ce que demande le contrat). Si la tentative est corrigée, le
    résumé du score est ajouté.
    """
    id = serializers.CharField(read_only=True)
    quiz_id = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    correct_answers = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'quiz_id', 'status', 'started_at', 'submitted_at',
            'answers', 'score', 'correct_answers', 'total_questions',
        ]

    def get_quiz_id(self, obj):
        return str(obj.quiz_id)

    def get_answers(self, obj):
        # Le quiz (avec ses questions) est passé en contexte pour éviter une requête par tentative.
        quiz = self.context.get('quiz') or obj.quiz
        selected = {a.question_id: a.selected_choice_id for a in obj.answers.all()}
        return {
            str(question.id): (str(selected[question.id]) if selected.get(question.id) else None)
            for question in quiz.questions.all()
        }

    def _evaluation(self, obj):
        # getattr avec défaut : une tentative non corrigée n'a pas d'évaluation.
        return getattr(obj, 'evaluation', None)

    def get_score(self, obj):
        evaluation = self._evaluation(obj)
        return int(evaluation.score) if evaluation else None

    def get_correct_answers(self, obj):
        evaluation = self._evaluation(obj)
        return evaluation.correct_answers if evaluation else None

    def get_total_questions(self, obj):
        evaluation = self._evaluation(obj)
        return evaluation.total_questions if evaluation else None


class AnswerMapSerializer(serializers.Serializer):
    """
    Corps de PATCH /attempts/<id>/ : {"answers": {"<id_question>": <id_choix> | null}}.
    Vérifie que chaque question appartient au quiz et que chaque choix
    appartient bien à SA question. Le quiz est fourni via le contexte.
    """
    answers = serializers.DictField(child=serializers.IntegerField(allow_null=True))

    def validate_answers(self, answers):
        questions = {q.id: q for q in self.context['quiz'].questions.all()}
        valid_choices = {qid: {c.id for c in q.choices.all()} for qid, q in questions.items()}

        cleaned, errors = {}, {}
        for key, choice_id in answers.items():
            try:
                question_id = int(key)
            except (TypeError, ValueError):
                errors[key] = ['Question ids must be numbers.']
                continue
            if question_id not in questions:
                errors[key] = ['This question does not belong to this quiz.']
            elif choice_id is not None and choice_id not in valid_choices[question_id]:
                errors[key] = ['This choice does not belong to this question.']
            else:
                cleaned[question_id] = choice_id  # None = on efface la réponse
        if errors:
            raise serializers.ValidationError(errors)
        return cleaned


def save_answers(attempt, cleaned_answers):
    """
    Enregistre (ou met à jour) les réponses envoyées ; les questions non
    mentionnées restent inchangées. `is_correct` n'est calculé qu'à la soumission.
    """
    for question_id, choice_id in cleaned_answers.items():
        Answer.objects.update_or_create(
            attempt=attempt, question_id=question_id,
            defaults={'selected_choice_id': choice_id, 'is_correct': False},
        )


class EvaluationSerializer(serializers.ModelSerializer):
    """Résultat d'une tentative corrigée, au format du contrat."""
    attempt_id = serializers.SerializerMethodField()
    quiz_id = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = [
            'attempt_id', 'quiz_id', 'score', 'correct_answers', 'total_questions',
            'feedback', 'question_feedback', 'next_steps', 'created_at',
        ]

    def get_attempt_id(self, obj):
        return str(obj.attempt_id)

    def get_quiz_id(self, obj):
        return str(obj.attempt.quiz_id)

    def get_score(self, obj):
        return int(obj.score)  # compte, pas pourcentage


# ---------------------------------------------------------------------------
# Étape 5 : exercices
# ---------------------------------------------------------------------------
class ExerciseChoiceStudentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = ExerciseChoice
        fields = ['id', 'text']  # jamais is_correct côté étudiant


class ExerciseChoiceTeacherSerializer(ExerciseChoiceStudentSerializer):
    class Meta(ExerciseChoiceStudentSerializer.Meta):
        fields = ['id', 'text', 'is_correct']


class ExerciseStudentSerializer(serializers.ModelSerializer):
    """Forme du contrat : {id, title, description, prompt, choices: [{id, text}]} (+ liens)."""
    id = serializers.CharField(read_only=True)
    course_id = serializers.SerializerMethodField()
    quiz_id = serializers.SerializerMethodField()
    choices = ExerciseChoiceStudentSerializer(many=True, read_only=True)

    class Meta:
        model = Exercise
        fields = ['id', 'course_id', 'quiz_id', 'title', 'description', 'prompt', 'choices']

    def get_course_id(self, obj):
        return str(obj.course_id) if obj.course_id else None

    def get_quiz_id(self, obj):
        return str(obj.quiz_id) if obj.quiz_id else None


class ExerciseTeacherSerializer(ExerciseStudentSerializer):
    """Le professeur voit en plus les bonnes réponses, l'explication et l'état de publication."""
    choices = ExerciseChoiceTeacherSerializer(many=True, read_only=True)
    author_id = serializers.SerializerMethodField()

    class Meta(ExerciseStudentSerializer.Meta):
        fields = ExerciseStudentSerializer.Meta.fields + [
            'explanation', 'status', 'author_id', 'created_at', 'published_at',
        ]

    def get_author_id(self, obj):
        return str(obj.created_by_id) if obj.created_by_id else None


def _save_exercise_choices(exercise, choices):
    """Crée les choix ; l'ordre de la liste devient `order`."""
    ExerciseChoice.objects.bulk_create([
        ExerciseChoice(exercise=exercise, order=index, **choice)
        for index, choice in enumerate(choices)
    ])


class ExerciseWriteSerializer(serializers.ModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(source='course', queryset=Course.objects.all())
    # quiz_id est facultatif : un exercice peut exister sans quiz.
    quiz_id = serializers.PrimaryKeyRelatedField(
        source='quiz', queryset=Quiz.objects.all(), required=False, allow_null=True,
    )
    title = serializers.CharField(max_length=255)
    choices = ChoiceInputSerializer(many=True, required=False)

    class Meta:
        model = Exercise
        fields = ['course_id', 'quiz_id', 'title', 'description', 'prompt', 'explanation', 'choices']

    def validate(self, attrs):
        # En PATCH, on complète avec les valeurs déjà enregistrées pour comparer.
        course = attrs.get('course', self.instance.course if self.instance else None)
        quiz = attrs.get('quiz', self.instance.quiz if self.instance else None)
        if quiz is not None:
            user = self.context['request'].user
            # Un professeur ne peut lier que SES quiz (message neutre : on ne révèle pas ceux des autres).
            if not is_admin(user) and quiz.created_by_id != user.id:
                raise serializers.ValidationError({'quiz_id': ['This quiz does not exist.']})
            if course is not None and quiz.course_id != course.id:
                raise serializers.ValidationError({'quiz_id': ['This quiz belongs to a different course.']})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        choices = validated_data.pop('choices', [])
        # L'auteur est toujours l'utilisateur connecté.
        exercise = Exercise.objects.create(created_by=self.context['request'].user, **validated_data)
        _save_exercise_choices(exercise, choices)
        return exercise

    @transaction.atomic
    def update(self, instance, validated_data):
        choices = validated_data.pop('choices', None)
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        if choices is not None:  # la liste envoyée REMPLACE tous les choix (exercice encore en brouillon)
            instance.choices.all().delete()
            _save_exercise_choices(instance, choices)
        return instance


def exercise_publish_errors(exercise):
    """Problèmes qui empêchent la publication d'un exercice (liste vide = prêt)."""
    choices = list(exercise.choices.all())
    correct = [choice for choice in choices if choice.is_correct]
    errors = []
    if len(choices) < 2:
        errors.append('An exercise needs at least 2 choices.')
    if len(correct) != 1:
        errors.append('An exercise needs exactly 1 correct choice.')
    return errors


class ExerciseAnswerSerializer(serializers.Serializer):
    """Corps de POST /submissions/ : {"answer": <id du choix>} ; l'exercice vient du contexte."""
    answer = serializers.IntegerField()

    def validate_answer(self, value):
        choice = next((c for c in self.context['exercise'].choices.all() if c.id == value), None)
        if choice is None:
            raise serializers.ValidationError('This choice does not belong to this exercise.')
        return choice  # on renvoie l'objet ExerciseChoice, pas seulement l'id


class ExerciseSubmissionSerializer(serializers.ModelSerializer):
    """Résultat d'une réponse : is_correct + feedback destiné à l'étudiant."""
    id = serializers.CharField(read_only=True)
    exercise_id = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

    class Meta:
        model = ExerciseSubmission
        fields = ['id', 'exercise_id', 'answer', 'is_correct', 'feedback', 'submitted_at']

    def get_exercise_id(self, obj):
        return str(obj.exercise_id)

    def get_answer(self, obj):
        return str(obj.selected_choice_id) if obj.selected_choice_id else None