"""
Vues du module `assessment`.

Étape 2 : routes de quiz (liste/création, détail/modification/suppression, publication).
Étape 3 : routes de tentatives (démarrer, sauvegarder, soumettre, évaluation).
Les routes restantes (exercices, génération) pointent encore vers `NotImplementedView` (501).
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

from .models import PublishStatus, Quiz, QuizAttempt
from .permissions import IsStudent, IsTeacher, IsTeacherOrReadOnly, is_admin, is_teacher
from .scoring import evaluate_attempt
from .serializers import (
    AnswerMapSerializer, AttemptSerializer, EvaluationSerializer,
    QuizDetailStudentSerializer, QuizDetailTeacherSerializer, QuizListSerializer,
    QuizWriteSerializer, publish_errors, save_answers,
)


@api_view(['GET'])
def api_root(request):
    # Page d'accueil de l'API : liste des grandes ressources.
    return Response({
        'quizzes': request.build_absolute_uri('quizzes/'),
        'exercises': request.build_absolute_uri('exercises/'),
        'generations': request.build_absolute_uri('generations/'),
    })


class NotImplementedView(APIView):
    """Vue temporaire (501) pour les routes pas encore codées."""

    def _not_implemented(self, request, *args, **kwargs):
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    get = post = patch = delete = _not_implemented


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


# ---------------------------------------------------------------------------
# GET/POST /quizzes/
# ---------------------------------------------------------------------------
class QuizListCreateView(ContractErrorsMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    serializer_class = QuizListSerializer  # liste paginée : {count, next, previous, results}

    def get_queryset(self):
        return visible_quizzes(self.request.user)

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