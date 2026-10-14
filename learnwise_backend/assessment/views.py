"""
Vues du module `assessment`.

Étape 2 : les 3 routes de quiz sont réelles (liste/création, détail/modification/
suppression, publication). Les autres routes pointent encore vers
`NotImplementedView` (réponse 501) et seront remplacées aux étapes suivantes.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PublishStatus, Quiz
from .permissions import IsTeacher, IsTeacherOrReadOnly, is_admin, is_teacher
from .serializers import (
    QuizDetailStudentSerializer, QuizDetailTeacherSerializer, QuizListSerializer,
    QuizWriteSerializer, publish_errors,
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