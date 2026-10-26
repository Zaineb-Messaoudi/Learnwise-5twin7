from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse, Http404
from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial, VideoMaterial, Transcription, Summary
from .serializers import (
    CourseSerializer, ChapterSerializer, CourseMaterialSerializer,
    AudioMaterialSerializer, DocumentMaterialSerializer, VideoMaterialSerializer,
    TranscriptionSerializer, SummarySerializer,
)


def _require_professor_or_admin(user):
    """Vérifie que l'utilisateur est professeur ou admin, sinon lève PermissionDenied."""
    if not (user and user.is_authenticated and (user.role == 'professeur' or user.is_superuser or user.role == 'admin')):
        raise PermissionDenied("Seuls les professeurs et administrateurs peuvent effectuer cette action.")


class CourseViewSet(viewsets.ModelViewSet):
    """
    CRUD des cours + actions avancées : publier, archiver, stats.
    - Professeur/Admin : CRUD complet sur ses propres cours.
    - Étudiant : lecture seule des cours publiés.
    """
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.all().annotate(
            materials_count=Count('materials'),
            chapters_count=Count('chapters'),
        )

        # Filtres avancés
        status = self.request.query_params.get('status')
        level = self.request.query_params.get('level')
        language = self.request.query_params.get('language')
        search = self.request.query_params.get('search')
        owner = self.request.query_params.get('owner')

        if status:
            qs = qs.filter(status=status)
        if level:
            qs = qs.filter(level__icontains=level)
        if language:
            qs = qs.filter(language__icontains=language)
        if owner:
            qs = qs.filter(owner__id=owner)

        # Un étudiant ne voit que les cours publiés
        if user.role == 'etudiant':
            qs = qs.filter(status='published')
        elif user.role == 'professeur':
            # Par défaut, un professeur voit ses cours + les publiés
            if not self.request.query_params.get('mine_only'):
                qs = qs.filter(Q(owner=user) | Q(status='published'))
            else:
                qs = qs.filter(owner=user)

        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        return qs.distinct()

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        course = self.get_object()
        if course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")
        instance.delete()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        course = self.get_object()
        _require_professor_or_admin(request.user)
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        course.status = 'published'
        course.save(update_fields=['status', 'updated_at'])
        return Response(CourseSerializer(course, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def archive(self, request, pk=None):
        course = self.get_object()
        _require_professor_or_admin(request.user)
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        course.status = 'archived'
        course.save(update_fields=['status', 'updated_at'])
        return Response(CourseSerializer(course, context={'request': request}).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        user = request.user
        if user.role == 'etudiant':
            qs = Course.objects.filter(status='published')
        else:
            qs = Course.objects.filter(owner=user)
        data = {
            'total': qs.count(),
            'draft': qs.filter(status='draft').count(),
            'published': qs.filter(status='published').count(),
            'archived': qs.filter(status='archived').count(),
        }
        return Response(data)


class ChapterViewSet(viewsets.ModelViewSet):
    """
    CRUD des chapitres d'un cours.
    - Professeur/Admin : CRUD complet sur les chapitres de leurs cours.
    - Étudiant : lecture seule des chapitres des cours publiés.
    """
    serializer_class = ChapterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Chapter.objects.all().annotate(materials_count=Count('materials'))

        course_id = self.request.query_params.get('course')
        if course_id:
            qs = qs.filter(course_id=course_id)

        # Un étudiant ne voit que les chapitres des cours publiés
        if user.role == 'etudiant':
            qs = qs.filter(course__status='published')
        elif user.role == 'professeur':
            qs = qs.filter(Q(course__owner=user) | Q(course__status='published'))

        return qs.distinct()

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        course = get_object_or_404(Course, pk=serializer.validated_data['course'].pk)
        if course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")
        serializer.save()

    def perform_update(self, serializer):
        chapter = self.get_object()
        if chapter.course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Non autorisé.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Non autorisé.")
        instance.delete()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)


class CourseMaterialViewSet(viewsets.ModelViewSet):
    """
    CRUD des matériels de cours + téléchargement de fichier.
    Un matériau peut appartenir à un chapitre (chapter) ou être au niveau du cours (chapter=null).
    """
    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = CourseMaterial.objects.all()
        course_id = self.request.query_params.get('course')
        chapter_id = self.request.query_params.get('chapter')
        material_type = self.request.query_params.get('material_type')

        if course_id:
            qs = qs.filter(course_id=course_id)
        if chapter_id:
            qs = qs.filter(chapter_id=chapter_id)
        if material_type:
            qs = qs.filter(material_type=material_type)

        user = self.request.user
        if user.role == 'etudiant':
            qs = qs.filter(course__status='published')
        elif user.role == 'professeur':
            qs = qs.filter(Q(course__owner=user) | Q(course__status='published'))

        return qs.distinct()

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        course = get_object_or_404(Course, pk=serializer.validated_data['course'].pk)
        if course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")

        chapter = serializer.validated_data.get('chapter')
        if chapter and chapter.course_id != course.id:
            raise PermissionDenied("Ce chapitre n'appartient pas à ce cours.")

        serializer.save()

    def perform_update(self, serializer):
        material = self.get_object()
        if material.course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Non autorisé.")

        chapter = serializer.validated_data.get('chapter')
        if chapter and chapter.course_id != material.course_id:
            raise PermissionDenied("Ce chapitre n'appartient pas à ce cours.")

        serializer.save()

    def perform_destroy(self, instance):
        if instance.course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Non autorisé.")
        instance.delete()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def download(self, request, pk=None):
        material = self.get_object()
        if not material.file:
            raise Http404("Fichier introuvable.")
        user = request.user
        if user.role == 'etudiant' and material.course.status != 'published':
            return Response({'detail': 'Cours non publié.'}, status=status.HTTP_403_FORBIDDEN)
        if user.role == 'professeur' and material.course.owner != user and not user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            response = FileResponse(material.file.open('rb'), as_attachment=True, filename=material.title)
            return response
        except FileNotFoundError:
            raise Http404("Fichier introuvable sur le disque.")


class AudioMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = AudioMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AudioMaterial.objects.all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)


class DocumentMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DocumentMaterial.objects.all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)


class VideoMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = VideoMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = VideoMaterial.objects.all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)


class TranscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = TranscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Transcription.objects.all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)


class SummaryViewSet(viewsets.ModelViewSet):
    serializer_class = SummarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Summary.objects.all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
