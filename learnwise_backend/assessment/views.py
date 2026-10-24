"""
Vues du module `assessment`.

Étape 2 : routes de quiz (liste/création, détail/modification/suppression, publication).
Étape 3 : routes de tentatives (démarrer, sauvegarder, soumettre, évaluation).
Étape 5 : routes d'exercices (liste/création, détail, publication, soumission d'une réponse).
Étape 6 : génération IA (lancer un job, suivre son état par polling).
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .generation import ACTIVE_STATUSES, MAX_ACTIVE_JOBS_PER_USER, dispatch, fail_stale_jobs
from .models import Exercise, ExerciseSubmission, GenerationJob, PublishStatus, Quiz, QuizAttempt
from .permissions import IsStudent, IsTeacher, IsTeacherOrReadOnly, is_admin, is_teacher
from .scoring import evaluate_attempt, grade_exercise
from .serializers import (
    AnswerMapSerializer, AttemptSerializer, EvaluationSerializer, ExerciseAnswerSerializer,
    ExerciseStudentSerializer, ExerciseSubmissionSerializer, ExerciseTeacherSerializer,
    ExerciseWriteSerializer, GenerationRequestSerializer, GenerationSerializer,
    QuizDetailStudentSerializer, QuizDetailTeacherSerializer, QuizListSerializer,
    QuizWriteSerializer, exercise_publish_errors, publish_errors, save_answers,
)


@api_view(['GET'])
def api_root(request):
    # Page d'accueil de l'API : liste des grandes ressources.
    return Response({
        'quizzes': request.build_absolute_uri('quizzes/'),
        'exercises': request.build_absolute_uri('exercises/'),
        'generations': request.build_absolute_uri('generations/'),
    })


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------
class Conflict(APIException):
    """HTTP 409 : l'action est impossible dans l'état actuel (ex : quiz déjà publié)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This action is not possible in the current state.'
    default_code = 'conflict'


class ContractErrorsMixin:
    """
    Met les erreurs de validation au format exigé par le contrat :
    {"detail": "Correct the highlighted fields.", "errors": {"champ": ["..."]}}
    """

    def handle_exception(self, exc):
        if isinstance(exc, ValidationError):
            errors = exc.detail
            if not isinstance(errors, dict):  # erreur globale : on la range sous une clé
                errors = {'non_field_errors': errors}
            return Response(
                {'detail': 'Correct the highlighted fields.', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().handle_exception(exc)


def visible_quizzes(user):
    """
    Quiz que cet utilisateur a le droit de voir :
    - admin      : tous ;
    - professeur : les siens (brouillons et publiés) ;
    - étudiant   : seulement les quiz publiés.
    prefetch_related charge questions et choix en 3 requêtes au total.
    """
    queryset = Quiz.objects.prefetch_related('questions__choices')
    if is_admin(user):
        return queryset
    if is_teacher(user):
        return queryset.filter(created_by=user)
    return queryset.filter(status=PublishStatus.PUBLISHED)


def detail_serializer_class(user):
    """Le professeur voit les bonnes réponses, l'étudiant non."""
    return QuizDetailTeacherSerializer if is_teacher(user) else QuizDetailStudentSerializer


def detail_response(request, quiz, http_status=status.HTTP_200_OK):
    """Recharge le quiz (le cache de prefetch serait périmé après une écriture) puis le sérialise."""
    quiz = visible_quizzes(request.user).get(pk=quiz.pk)
    data = detail_serializer_class(request.user)(quiz, context={'request': request}).data
    return Response(data, status=http_status)


def filter_by_course(queryset, request):
    """
    Filtre de liste `?course=<id>` utilisé par le frontend pour n'afficher que les
    quiz / exercices d'un cours. Sans paramètre, rien ne change ; avec un id
    invalide, on répond 400 au format du contrat (au lieu d'ignorer l'erreur).
    """
    course = request.query_params.get('course')
    if course in (None, ''):
        return queryset
    try:
        course_id = int(course)
    except ValueError:
        raise ValidationError({'course': ['A valid course id is required.']})
    return queryset.filter(course_id=course_id)


# ---------------------------------------------------------------------------
# GET/POST /quizzes/
# ---------------------------------------------------------------------------
class QuizListCreateView(ContractErrorsMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    serializer_class = QuizListSerializer  # liste paginée : {count, next, previous, results}

    def get_queryset(self):
        # Visibilité selon le rôle, puis filtre facultatif ?course=<id>.
        return filter_by_course(visible_quizzes(self.request.user), self.request)

    def create(self, request, *args, **kwargs):
        serializer = QuizWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        quiz = serializer.save()
        return detail_response(request, quiz, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# GET/PATCH/DELETE /quizzes/<quiz_id>/
# ---------------------------------------------------------------------------
class QuizDetailView(ContractErrorsMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    lookup_url_kwarg = 'quiz_id'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']  # pas de PUT (le contrat ne le prévoit pas)

    def get_queryset(self):
        return visible_quizzes(self.request.user)

    def get_serializer_class(self):
        return detail_serializer_class(self.request.user)

    def partial_update(self, request, *args, **kwargs):
        quiz = self.get_object()
        if quiz.status != PublishStatus.DRAFT:
            raise Conflict('Only draft quizzes can be edited.')
        serializer = QuizWriteSerializer(
            quiz, data=request.data, partial=True, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return detail_response(request, quiz)

    def destroy(self, request, *args, **kwargs):
        quiz = self.get_object()
        if quiz.status != PublishStatus.DRAFT:
            # Supprimer un quiz publié effacerait aussi les tentatives des étudiants.
            raise Conflict('Only draft quizzes can be deleted.')
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /quizzes/<quiz_id>/publish/
# ---------------------------------------------------------------------------
class QuizPublishView(ContractErrorsMixin, APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, quiz_id):
        quiz = get_object_or_404(visible_quizzes(request.user), pk=quiz_id)
        if quiz.status == PublishStatus.PUBLISHED:
            raise Conflict('This quiz is already published.')
        problems = publish_errors(quiz)
        if problems:
            raise ValidationError({'questions': problems})
        quiz.status = PublishStatus.PUBLISHED
        quiz.published_at = timezone.now()
        quiz.save(update_fields=['status', 'published_at', 'updated_at'])
        return detail_response(request, quiz)


# ===========================================================================
# Étape 3 : tentatives (réservées aux étudiants, privées à chaque étudiant)
# ===========================================================================
def get_published_quiz(quiz_id):
    """Quiz publié avec questions et choix préchargés ; 404 sinon (brouillon ou inconnu)."""
    return get_object_or_404(
        Quiz.objects.prefetch_related('questions__choices'),
        pk=quiz_id, status=PublishStatus.PUBLISHED,
    )


def attempts_of(user):
    """Tentatives de CET étudiant uniquement (un étudiant ne voit jamais celles des autres)."""
    return QuizAttempt.objects.filter(user=user).select_related('evaluation').prefetch_related('answers')


def attempt_response(request, attempt, quiz, http_status=status.HTTP_200_OK):
    """Recharge la tentative (cache périmé après écriture) et renvoie sa représentation."""
    attempt = attempts_of(request.user).get(pk=attempt.pk)
    data = AttemptSerializer(attempt, context={'request': request, 'quiz': quiz}).data
    return Response(data, status=http_status)


class AttemptListCreateView(ContractErrorsMixin, generics.ListCreateAPIView):
    """GET : mes tentatives sur ce quiz. POST : démarrer (ou reprendre la tentative en cours)."""
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = AttemptSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['quiz'] = get_published_quiz(self.kwargs['quiz_id'])
        return context

    def get_queryset(self):
        get_published_quiz(self.kwargs['quiz_id'])  # 404 si le quiz n'est pas publié
        return attempts_of(self.request.user).filter(quiz_id=self.kwargs['quiz_id'])

    def create(self, request, *args, **kwargs):
        quiz = get_published_quiz(kwargs['quiz_id'])
        # get_or_create : renvoie la tentative en cours si elle existe, sinon en crée une.
        # La contrainte unique de la base protège contre deux clics simultanés.
        attempt, created = QuizAttempt.objects.get_or_create(
            user=request.user, quiz=quiz, status=QuizAttempt.Status.IN_PROGRESS,
        )
        # Contrat : 201 pour une nouvelle tentative, 200 si on renvoie celle déjà en cours.
        return attempt_response(
            request, attempt, quiz,
            status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AttemptDetailView(ContractErrorsMixin, generics.GenericAPIView):
    """GET : reprendre une tentative. PATCH : sauvegarder les réponses sans soumettre."""
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = AttemptSerializer

    def get_attempt(self):
        return get_object_or_404(
            attempts_of(self.request.user),
            pk=self.kwargs['attempt_id'], quiz_id=self.kwargs['quiz_id'],
        )

    def get(self, request, quiz_id, attempt_id):
        attempt = self.get_attempt()
        return attempt_response(request, attempt, get_published_quiz(quiz_id))

    def patch(self, request, quiz_id, attempt_id):
        attempt = self.get_attempt()
        if attempt.status != QuizAttempt.Status.IN_PROGRESS:
            raise Conflict('This attempt has already been submitted.')
        quiz = get_published_quiz(quiz_id)
        serializer = AnswerMapSerializer(data=request.data, context={'quiz': quiz})
        serializer.is_valid(raise_exception=True)
        save_answers(attempt, serializer.validated_data['answers'])
        return attempt_response(request, attempt, quiz)


class AttemptSubmitView(ContractErrorsMixin, APIView):
    """POST : corrige la tentative et renvoie l'évaluation. On peut joindre les dernières réponses."""
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, quiz_id, attempt_id):
        quiz = get_published_quiz(quiz_id)
        with transaction.atomic():
            # select_for_update : deux soumissions simultanées ne corrigent pas deux fois.
            attempt = get_object_or_404(
                QuizAttempt.objects.select_for_update().filter(user=request.user),
                pk=attempt_id, quiz_id=quiz_id,
            )
            if attempt.status != QuizAttempt.Status.IN_PROGRESS:
                raise Conflict('This attempt has already been submitted.')
            if 'answers' in request.data:  # réponses finales envoyées avec la soumission
                serializer = AnswerMapSerializer(data=request.data, context={'quiz': quiz})
                serializer.is_valid(raise_exception=True)
                save_answers(attempt, serializer.validated_data['answers'])
            evaluation = evaluate_attempt(attempt)
        return Response(EvaluationSerializer(evaluation).data, status=status.HTTP_200_OK)


class AttemptEvaluationView(ContractErrorsMixin, APIView):
    """GET : relire le score, le feedback par question et les prochaines étapes."""
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request, quiz_id, attempt_id):
        attempt = get_object_or_404(
            attempts_of(request.user), pk=attempt_id, quiz_id=quiz_id,
        )
        evaluation = getattr(attempt, 'evaluation', None)
        if evaluation is None:
            raise NotFound('This attempt has not been submitted yet.')
        return Response(EvaluationSerializer(evaluation).data)


# ===========================================================================
# Étape 5 : exercices (mêmes règles de visibilité que les quiz)
# ===========================================================================
def visible_exercises(user):
    """
    Exercices que cet utilisateur peut voir :
    admin = tous ; professeur = les siens ; étudiant = seulement les publiés.
    """
    queryset = Exercise.objects.prefetch_related('choices')
    if is_admin(user):
        return queryset
    if is_teacher(user):
        return queryset.filter(created_by=user)
    return queryset.filter(status=PublishStatus.PUBLISHED)


def exercise_serializer_class(user):
    """Le professeur voit les bonnes réponses, l'étudiant non."""
    return ExerciseTeacherSerializer if is_teacher(user) else ExerciseStudentSerializer


def exercise_response(request, exercise, http_status=status.HTTP_200_OK):
    """Recharge l'exercice (cache de prefetch périmé après écriture) puis le sérialise."""
    exercise = visible_exercises(request.user).get(pk=exercise.pk)
    data = exercise_serializer_class(request.user)(exercise, context={'request': request}).data
    return Response(data, status=http_status)


class ExerciseListCreateView(ContractErrorsMixin, generics.ListCreateAPIView):
    """GET : liste paginée selon le rôle. POST : le professeur crée un brouillon."""
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def get_queryset(self):
        # Visibilité selon le rôle, puis filtre facultatif ?course=<id>.
        return filter_by_course(visible_exercises(self.request.user), self.request)

    def get_serializer_class(self):
        return exercise_serializer_class(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = ExerciseWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        exercise = serializer.save()
        return exercise_response(request, exercise, status.HTTP_201_CREATED)


class ExerciseDetailView(ContractErrorsMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE : modification et suppression réservées aux brouillons."""
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    lookup_url_kwarg = 'exercise_id'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']  # pas de PUT

    def get_queryset(self):
        return visible_exercises(self.request.user)

    def get_serializer_class(self):
        return exercise_serializer_class(self.request.user)

    def partial_update(self, request, *args, **kwargs):
        exercise = self.get_object()
        if exercise.status != PublishStatus.DRAFT:
            raise Conflict('Only draft exercises can be edited.')
        serializer = ExerciseWriteSerializer(
            exercise, data=request.data, partial=True, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return exercise_response(request, exercise)

    def destroy(self, request, *args, **kwargs):
        exercise = self.get_object()
        if exercise.status != PublishStatus.DRAFT:
            # Supprimer un exercice publié effacerait les soumissions des étudiants.
            raise Conflict('Only draft exercises can be deleted.')
        exercise.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExercisePublishView(ContractErrorsMixin, APIView):
    """POST : publie un exercice complet (au moins 2 choix, exactement 1 bonne réponse)."""
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, exercise_id):
        exercise = get_object_or_404(visible_exercises(request.user), pk=exercise_id)
        if exercise.status == PublishStatus.PUBLISHED:
            raise Conflict('This exercise is already published.')
        problems = exercise_publish_errors(exercise)
        if problems:
            raise ValidationError({'choices': problems})
        exercise.status = PublishStatus.PUBLISHED
        exercise.published_at = timezone.now()
        exercise.save(update_fields=['status', 'published_at'])
        return exercise_response(request, exercise)


class ExerciseSubmissionView(ContractErrorsMixin, APIView):
    """
    POST : l'étudiant répond à un exercice publié et reçoit aussitôt is_correct + feedback.
    Il peut réessayer : chaque réponse est enregistrée comme une soumission distincte.
    """
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, exercise_id):
        exercise = get_object_or_404(
            Exercise.objects.prefetch_related('choices'),
            pk=exercise_id, status=PublishStatus.PUBLISHED,
        )
        serializer = ExerciseAnswerSerializer(data=request.data, context={'exercise': exercise})
        serializer.is_valid(raise_exception=True)
        choice = serializer.validated_data['answer']
        is_correct, feedback = grade_exercise(exercise, choice)
        submission = ExerciseSubmission.objects.create(
            exercise=exercise, user=request.user, selected_choice=choice,
            is_correct=is_correct, feedback=feedback,
        )
        return Response(ExerciseSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


# ===========================================================================
# Étape 6 : génération IA (réservée aux professeurs)
# ===========================================================================
class TooManyRequests(APIException):
    """HTTP 429 : trop de générations en cours pour cet utilisateur."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Too many generations in progress.'
    default_code = 'too_many_requests'


class GenerationCreateView(ContractErrorsMixin, APIView):
    """POST : valide la demande, crée un job "queued" et lance le travail en arrière-plan."""
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        serializer = GenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Chaque génération consomme le quota de la clé API : on limite les jobs simultanés.
        fail_stale_jobs()  # libère d'abord les jobs bloqués, sinon ils compteraient à tort
        active = GenerationJob.objects.filter(
            requested_by=request.user, status__in=ACTIVE_STATUSES,
        ).count()
        if active >= MAX_ACTIVE_JOBS_PER_USER:
            raise TooManyRequests(
                'You already have several generations in progress. Wait for one to finish.'
            )

        job = GenerationJob.objects.create(
            requested_by=request.user,
            course=data['course'],
            kind=data['kind'],
            question_count=data['question_count'],
            difficulty=data['difficulty'],
            source_text=data['source_text'].strip(),
            material_ids=data['material_ids'],
        )
        dispatch(job)
        job.refresh_from_db()  # le statut a pu changer si le traitement est déjà fini
        return Response(GenerationSerializer(job).data, status=status.HTTP_201_CREATED)


class GenerationDetailView(ContractErrorsMixin, APIView):
    """GET : état du job (polling) et, une fois "completed", les questions proposées."""
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request, generation_id):
        fail_stale_jobs()
        jobs = GenerationJob.objects.all() if is_admin(request.user) else GenerationJob.objects.filter(
            requested_by=request.user,  # un professeur ne voit que ses propres générations
        )
        job = get_object_or_404(jobs, pk=generation_id)
        return Response(GenerationSerializer(job).data)