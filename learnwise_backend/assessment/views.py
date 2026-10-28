from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Quiz, Question, Choice, QuizAttempt, Answer, Evaluation, Exercise
from .serializers import (
    QuizSerializer, QuestionSerializer, ChoiceSerializer,
    QuizAttemptSerializer, AnswerSerializer, EvaluationSerializer, ExerciseSerializer,
)
from content.models import Course


class IsOwnerOrAdmin(permissions.BasePermission):
    """Object-level permission: only the owner of the related course or an admin."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or user.role == 'admin':
            return True
        # obj may be a Quiz, Question, Choice, Exercise, etc.
        course = getattr(obj, 'course', None)
        if course is None:
            course = getattr(obj, 'quiz', None)
            if course is not None:
                course = course.course
        return course is not None and course.owner == user


class QuizGenerationViewSet(viewsets.ViewSet):
    """AI quiz generation endpoints - not yet implemented."""
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        return Response({'detail': 'Quiz generation not yet implemented.', 'id': None}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def retrieve(self, request, pk=None):
        return Response({'detail': 'Generation not found.'}, status=status.HTTP_404_NOT_FOUND)


class QuizViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Quiz.objects.select_related('course', 'course__owner').all()
        if user.is_superuser or user.role == 'admin':
            return qs
        return qs.filter(Q(course__owner=user) | Q(course__status='published'))

    def perform_create(self, serializer):
        course_id = self.request.data.get('course')
        if not course_id:
            raise status.HTTP_400_BAD_REQUEST.__class__('course is required')
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise status.HTTP_404_NOT_FOUND.__class__('Course not found')
        if course.owner != self.request.user and not self.request.user.is_superuser:
            raise permissions.PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")
        serializer.save()

    def perform_update(self, serializer):
        quiz = self.get_object()
        if quiz.course.owner != self.request.user and not self.request.user.is_superuser:
            raise permissions.PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.course.owner != self.request.user and not self.request.user.is_superuser:
            raise permissions.PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")
        instance.delete()

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        quiz = self.get_object()
        if quiz.course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'detail': 'Quiz published.'})

    @action(detail=True, methods=['get', 'post'])
    def attempts(self, request, pk=None):
        quiz = self.get_object()
        if request.method == 'GET':
            attempts = QuizAttempt.objects.filter(quiz=quiz, user=request.user)
            return Response(QuizAttemptSerializer(attempts, many=True).data)
        # POST - start attempt
        attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz)
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='attempts/(?P<attempt_id>\\d+)/submit')
    def submit(self, request, pk=None, attempt_id=None):
        try:
            attempt = QuizAttempt.objects.get(id=attempt_id, quiz_id=pk, user=request.user)
        except QuizAttempt.DoesNotExist:
            return Response({'detail': 'Attempt not found.'}, status=status.HTTP_404_NOT_FOUND)
        answers = request.data.get('answers', {})
        # Save answers
        score = 0
        total = 0
        for question_id, answer_text in answers.items():
            try:
                question = Question.objects.get(id=question_id, quiz_id=pk)
                total += 1
                correct_choice = Choice.objects.filter(question=question, text=answer_text).first()
                is_correct = bool(correct_choice)
                if is_correct:
                    score += 1
            except (Question.DoesNotExist, ValueError):
                is_correct = False
                total += 1
            Answer.objects.create(
                attempt=attempt,
                question_id=question_id,
                is_correct=is_correct,
            )
        Evaluation.objects.update_or_create(
            attempt=attempt,
            defaults={'score': (score / total * 100) if total else 0, 'feedback': f'{score}/{total} correct'},
        )
        return Response({'detail': 'Attempt submitted.', 'score': (score / total * 100) if total else 0})

    @action(detail=True, methods=['get'], url_path='attempts/(?P<attempt_id>\\d+)/evaluation')
    def result(self, request, pk=None, attempt_id=None):
        try:
            attempt = QuizAttempt.objects.get(id=attempt_id, quiz_id=pk, user=request.user)
        except QuizAttempt.DoesNotExist:
            return Response({'detail': 'Attempt not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            eval_obj = attempt.evaluations.first()
            score = eval_obj.score if eval_obj else 0
            feedback = eval_obj.feedback if eval_obj else 'Evaluation pending.'
        except Evaluation.DoesNotExist:
            score = 0
            feedback = 'Evaluation pending.'
        return Response({
            'attempt_id': attempt.id,
            'score': score,
            'feedback': feedback,
        })


class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Question.objects.select_related('quiz', 'quiz__course', 'quiz__course__owner').all()
        if user.is_superuser or user.role == 'admin':
            return qs
        quiz_id = self.request.query_params.get('quiz')
        if quiz_id:
            qs = qs.filter(id=quiz_id)
        return qs.filter(Q(quiz__course__owner=user) | Q(quiz__course__status='published'))


class ChoiceViewSet(viewsets.ModelViewSet):
    serializer_class = ChoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Choice.objects.select_related('question', 'question__quiz', 'question__quiz__course', 'question__quiz__course__owner').all()
        if user.is_superuser or user.role == 'admin':
            return qs
        question_id = self.request.query_params.get('question')
        if question_id:
            qs = qs.filter(id=question_id)
        return qs.filter(Q(question__quiz__course__owner=user) | Q(question__quiz__course__status='published'))


class QuizAttemptViewSet(viewsets.ModelViewSet):
    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AnswerViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Answer.objects.filter(attempt__user=self.request.user)

    def perform_create(self, serializer):
        attempt_id = self.request.data.get('attempt')
        try:
            attempt = QuizAttempt.objects.get(id=attempt_id, user=self.request.user)
        except QuizAttempt.DoesNotExist:
            raise permissions.PermissionDenied("Attempt not found or not yours.")
        serializer.save(attempt=attempt)


class EvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Evaluation.objects.filter(attempt__user=self.request.user)


class ExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = ExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Exercise.objects.select_related('quiz', 'quiz__course', 'quiz__course__owner').all()
        if user.is_superuser or user.role == 'admin':
            return qs
        return qs.filter(Q(quiz__course__owner=user) | Q(quiz__course__status='published'))

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        exercise = self.get_object()
        answer = request.data.get('answer', '')
        return Response({'detail': 'Exercise submitted.', 'answer': answer})
