from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse, Http404
from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial, VideoMaterial, Transcription, Summary, CoursePresence, CourseVersion, CoursePrerequisite, LessonCompletion
from .serializers import (
    CourseSerializer, ChapterSerializer, CourseMaterialSerializer,
    AudioMaterialSerializer, DocumentMaterialSerializer, VideoMaterialSerializer,
    TranscriptionSerializer, SummarySerializer, CourseVersionSerializer, CoursePrerequisiteSerializer,
    LessonCompletionSerializer,
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
        elif not user.role:
            # role=None (not onboarded) sees nothing
            qs = qs.none()
        # admin/superuser sees everything (qs already unfiltered)

        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        return qs.distinct()

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        # API-created courses always enter the review workflow as drafts,
        # regardless of a client-supplied status or past schedule.
        serializer.save(owner=self.request.user, status='draft')

    def perform_update(self, serializer):
        course = self.get_object()
        if course.owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("Vous n'êtes pas le propriétaire de ce cours.")
        # Prevent bypassing the review workflow: only admins can publish directly.
        # Professors must use submit_for_review -> approve.
        if 'status' in serializer.validated_data:
            new_status = serializer.validated_data['status']
            if new_status == 'published' and course.status != 'published':
                if not (self.request.user.is_superuser or self.request.user.role == 'admin'):
                    raise PermissionDenied("Seuls les administrateurs peuvent publier directement. Utilisez 'submit_for_review'.")
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

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def presence(self, request, pk=None):
        """Return users currently viewing this course (WebSocket presence)."""
        course = self.get_object()
        presences = CoursePresence.objects.filter(course=course).select_related('user').order_by('-last_seen')
        data = [
            {
                'user_id': p.user.id,
                'email': p.user.email,
                'name': p.user.name if hasattr(p.user, 'name') else f'{p.user.first_name} {p.user.last_name}'.strip() or p.user.email,
                'role': p.user.role,
                'joined_at': p.joined_at.isoformat(),
                'last_seen': p.last_seen.isoformat(),
            }
            for p in presences
        ]
        return Response({'course_id': course.id, 'users': data, 'count': len(data)})

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def versions(self, request, pk=None):
        """List all version snapshots for this course."""
        course = self.get_object()
        versions = CourseVersion.objects.filter(course=course).order_by('-version_number')
        serializer = CourseVersionSerializer(versions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def create_version(self, request, pk=None):
        """Manually create a version snapshot of this course."""
        course = self.get_object()
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        change_description = request.data.get('change_description', '')
        version = CourseVersion.create_snapshot(course, request.user, change_description)
        serializer = CourseVersionSerializer(version, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rollback(self, request, pk=None):
        """Rollback this course to a previous version snapshot."""
        course = self.get_object()
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        version_id = request.data.get('version_id')
        if not version_id:
            return Response({'detail': 'version_id requis.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            version = CourseVersion.objects.get(id=version_id, course=course)
        except CourseVersion.DoesNotExist:
            return Response({'detail': 'Version introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        # Create a snapshot of current state before rolling back
        CourseVersion.create_snapshot(course, request.user, f'Auto-snapshot before rollback to v{version.version_number}')

        # Apply the target version
        version.apply_to(course)

        serializer = self.get_serializer(course)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def prerequisites(self, request, pk=None):
        """List or add prerequisites for this course."""
        course = self.get_object()
        if request.method == 'GET':
            prereqs = CoursePrerequisite.objects.filter(course=course).select_related('prerequisite_course')
            serializer = CoursePrerequisiteSerializer(prereqs, many=True, context={'request': request})
            return Response(serializer.data)

        # POST - add a prerequisite
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = CoursePrerequisiteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                serializer.save(course=course)
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated], url_path='prerequisites/(?P<prereq_id>\\d+)')
    def remove_prerequisite(self, request, pk=None, prereq_id=None):
        """Remove a prerequisite from this course."""
        course = self.get_object()
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            prereq = CoursePrerequisite.objects.get(id=prereq_id, course=course)
            prereq.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CoursePrerequisite.DoesNotExist:
            return Response({'detail': 'Prérequis introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def duplicate(self, request, pk=None):
        """Duplicate this course with all chapters and materials (draft status)."""
        course = self.get_object()
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        new_title = request.data.get('title', f"{course.title} (Copie)")

        # Duplicate course
        new_course = Course.objects.create(
            title=new_title,
            description=course.description,
            level=course.level,
            language=course.language,
            status='draft',
            content_type=course.content_type,
            markdown_content=course.markdown_content,
            latex_content=course.latex_content,
            owner=request.user,
        )

        # Duplicate chapters
        chapter_map = {}
        for chapter in course.chapters.all():
            new_chapter = Chapter.objects.create(
                course=new_course,
                title=chapter.title,
                description=chapter.description,
                order=chapter.order,
            )
            chapter_map[chapter.id] = new_chapter

        # Duplicate materials
        for material in course.materials.all():
            new_material = CourseMaterial.objects.create(
                course=new_course,
                chapter=chapter_map.get(material.chapter_id) if material.chapter_id else None,
                title=material.title,
                material_type=material.material_type,
            )
            # Copy file if exists
            if material.file:
                new_material.file = material.file
                new_material.file_size = material.file_size
            new_material.save()

            # Duplicate type-specific details
            if material.material_type == 'audio':
                try:
                    audio = material.audio_details
                    AudioMaterial.objects.create(
                        material=new_material,
                        duration=audio.duration,
                        language=audio.language,
                    )
                except AudioMaterial.DoesNotExist:
                    pass
            elif material.material_type == 'document':
                try:
                    doc = material.document_details
                    DocumentMaterial.objects.create(
                        material=new_material,
                        page_count=doc.page_count,
                        mime_type=doc.mime_type,
                    )
                except DocumentMaterial.DoesNotExist:
                    pass
            elif material.material_type == 'video':
                try:
                    video = material.video_details
                    VideoMaterial.objects.create(
                        material=new_material,
                        duration=video.duration,
                        resolution=video.resolution,
                        language=video.language,
                    )
                except VideoMaterial.DoesNotExist:
                    pass

        serializer = self.get_serializer(new_course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def export(self, request, pk=None):
        """Export course as ZIP: metadata JSON + all material files."""
        course = self.get_object()
        user = request.user
        if user.role == 'etudiant' and course.status != 'published':
            return Response({'detail': 'Cours non publié.'}, status=status.HTTP_403_FORBIDDEN)
        if user.role == 'professeur' and course.owner != user and not user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        import zipfile
        import io
        import json
        from django.utils import timezone

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Course metadata
            course_data = {
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'level': course.level,
                'language': course.language,
                'status': course.status,
                'content_type': course.content_type,
                'markdown_content': course.markdown_content,
                'latex_content': course.latex_content,
                'scheduled_publish_at': course.scheduled_publish_at.isoformat() if course.scheduled_publish_at else None,
                'estimated_reading_minutes': course.estimated_reading_minutes,
                'created_at': course.created_at.isoformat(),
                'updated_at': course.updated_at.isoformat(),
                'owner_email': course.owner.email if course.owner else None,
            }
            zf.writestr('course_metadata.json', json.dumps(course_data, indent=2, ensure_ascii=False))

            # Chapters
            chapters_data = []
            for chapter in course.chapters.all():
                chapters_data.append({
                    'id': chapter.id,
                    'title': chapter.title,
                    'description': chapter.description,
                    'order': chapter.order,
                    'created_at': chapter.created_at.isoformat(),
                })
            zf.writestr('chapters.json', json.dumps(chapters_data, indent=2, ensure_ascii=False))

            # Materials + files
            materials_data = []
            for material in course.materials.all():
                mat_entry = {
                    'id': material.id,
                    'title': material.title,
                    'material_type': material.material_type,
                    'file_size': material.file_size,
                    'uploaded_at': material.uploaded_at.isoformat(),
                    'file_name': None,
                }
                if material.file:
                    try:
                        mat_entry['file_name'] = material.file.name
                        # Use file.open() instead of .path for S3-compatible storage
                        with material.file.open('rb') as f:
                            zf.writestr(f"files/{material.file.name}", f.read())
                    except (FileNotFoundError, ValueError, NotImplementedError):
                        pass
                materials_data.append(mat_entry)
            zf.writestr('materials.json', json.dumps(materials_data, indent=2, ensure_ascii=False))

        buffer.seek(0)
        response = FileResponse(
            buffer,
            as_attachment=True,
            filename=f"course_{course.id}_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip",
        )
        response['Content-Type'] = 'application/zip'
        return response

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_for_review(self, request, pk=None):
        """Submit a draft course for admin review."""
        course = self.get_object()
        if course.owner != request.user and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        if course.status != 'draft':
            return Response({'detail': 'Seul un cours en brouillon peut être soumis.'}, status=status.HTTP_400_BAD_REQUEST)

        course.status = 'pending_review'
        course.save(update_fields=['status', 'updated_at'])
        return Response(CourseSerializer(course, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve a pending_review course (admin only)."""
        if not (request.user.is_superuser or request.user.role == 'admin'):
            return Response({'detail': 'Seuls les administrateurs peuvent approuver.'}, status=status.HTTP_403_FORBIDDEN)

        course = self.get_object()
        if course.status != 'pending_review':
            return Response({'detail': 'Ce cours n\'est pas en attente de révision.'}, status=status.HTTP_400_BAD_REQUEST)

        course.status = 'published'
        course.save(update_fields=['status', 'updated_at'])
        return Response(CourseSerializer(course, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a pending_review course, returning it to draft (admin only)."""
        if not (request.user.is_superuser or request.user.role == 'admin'):
            return Response({'detail': 'Seuls les administrateurs peuvent rejeter.'}, status=status.HTTP_403_FORBIDDEN)

        course = self.get_object()
        if course.status != 'pending_review':
            return Response({'detail': 'Ce cours n\'est pas en attente de révision.'}, status=status.HTTP_400_BAD_REQUEST)

        course.status = 'draft'
        course.save(update_fields=['status', 'updated_at'])
        return Response(CourseSerializer(course, context={'request': request}).data)


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
        elif not user.role:
            qs = qs.none()
        # admin/superuser sees everything

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
        # Prevent moving a chapter to another professor's course
        if 'course' in serializer.validated_data:
            new_course = serializer.validated_data['course']
            if new_course.id != chapter.course.id and new_course.owner != self.request.user and not self.request.user.is_superuser:
                raise PermissionDenied("Vous ne pouvez pas déplacer ce chapitre vers le cours d'un autre professeur.")
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
        elif not user.role:
            qs = qs.none()
        # admin/superuser sees everything

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

        # Prevent moving a material to another professor's course
        if 'course' in serializer.validated_data:
            new_course = serializer.validated_data['course']
            if new_course.id != material.course.id and new_course.owner != self.request.user and not self.request.user.is_superuser:
                raise PermissionDenied("Vous ne pouvez pas déplacer ce matériel vers le cours d'un autre professeur.")

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
        # Marquer le matériel comme complété pour l'étudiant (gating des quiz)
        if user.role == 'etudiant':
            LessonCompletion.objects.get_or_create(user=user, material=material)
        try:
            import os
            ext = os.path.splitext(material.file.name)[1]
            filename = material.title + (ext if ext and not material.title.endswith(ext) else '')
            response = FileResponse(material.file.open('rb'), as_attachment=True, filename=filename)
            return response
        except FileNotFoundError:
            raise Http404("Fichier introuvable sur le disque.")

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        material = self.get_object()
        if request.user.role != 'etudiant':
            return Response({'detail': 'Only students can complete lessons.'}, status=status.HTTP_403_FORBIDDEN)
        if material.course.status != 'published':
            return Response({'detail': 'Cours non publié.'}, status=status.HTTP_403_FORBIDDEN)
        completion, _ = LessonCompletion.objects.get_or_create(user=request.user, material=material)
        return Response(LessonCompletionSerializer(completion).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def processing(self, request, pk=None):
        return Response({'detail': 'Material processing is not available in this deployment.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def retry(self, request, pk=None):
        return Response({'detail': 'Material processing retry is not available in this deployment.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def transcription(self, request, pk=None):
        material = self.get_object()
        transcription = material.transcriptions.order_by('-created_at').first()
        if request.method == 'GET':
            if not transcription:
                return Response({'detail': 'No transcription exists.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(TranscriptionSerializer(transcription).data)
        if material.course.owner_id != request.user.id and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        if not transcription:
            transcription = Transcription.objects.create(material=material)
        serializer = TranscriptionSerializer(transcription, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def summary(self, request, pk=None):
        material = self.get_object()
        summary = material.summaries.order_by('-created_at').first()
        if request.method == 'GET':
            if not summary:
                return Response({'detail': 'No summary exists.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(SummarySerializer(summary).data)
        if material.course.owner_id != request.user.id and not request.user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        if not summary:
            summary = Summary.objects.create(material=material)
        serializer = SummarySerializer(summary, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def regenerate_summary(self, request, pk=None):
        return Response({'detail': 'Summary regeneration is not available in this deployment.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_thumbnail(self, request, pk=None):
        """Generate a thumbnail preview for this material using Pillow."""
        material = self.get_object()
        user = request.user
        if material.course.owner != user and not user.is_superuser:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        from content.thumbnail_utils import generate_thumbnail
        generate_thumbnail(material)
        material.save(update_fields=['thumbnail'])

        serializer = self.get_serializer(material)
        return Response(serializer.data)


class AudioMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = AudioMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AudioMaterial.objects.select_related('material__course', 'material__course__owner').all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)

        user = self.request.user
        if user.role == 'etudiant':
            qs = qs.filter(material__course__status='published')
        elif user.role == 'professeur':
            qs = qs.filter(Q(material__course__owner=user) | Q(material__course__status='published'))
        elif not user.role:
            qs = qs.none()
        return qs.distinct()

    def _check_material_owner(self, material, user):
        if material.course.owner != user and not user.is_superuser:
            raise PermissionDenied("Non autorisé sur ce matériel.")

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        material = get_object_or_404(CourseMaterial, pk=serializer.validated_data['material'].pk)
        self._check_material_owner(material, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        self._check_material_owner(obj.material, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_material_owner(instance.material, self.request.user)
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


class DocumentMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DocumentMaterial.objects.select_related('material__course', 'material__course__owner').all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)

        user = self.request.user
        if user.role == 'etudiant':
            qs = qs.filter(material__course__status='published')
        elif user.role == 'professeur':
            qs = qs.filter(Q(material__course__owner=user) | Q(material__course__status='published'))
        elif not user.role:
            qs = qs.none()
        return qs.distinct()

    def _check_material_owner(self, material, user):
        if material.course.owner != user and not user.is_superuser:
            raise PermissionDenied("Non autorisé sur ce matériel.")

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        material = get_object_or_404(CourseMaterial, pk=serializer.validated_data['material'].pk)
        self._check_material_owner(material, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        self._check_material_owner(obj.material, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_material_owner(instance.material, self.request.user)
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


class VideoMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = VideoMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = VideoMaterial.objects.select_related('material__course', 'material__course__owner').all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)

        user = self.request.user
        if user.role == 'etudiant':
            qs = qs.filter(material__course__status='published')
        elif user.role == 'professeur':
            qs = qs.filter(Q(material__course__owner=user) | Q(material__course__status='published'))
        elif not user.role:
            qs = qs.none()
        return qs.distinct()

    def _check_material_owner(self, material, user):
        if material.course.owner != user and not user.is_superuser:
            raise PermissionDenied("Non autorisé sur ce matériel.")

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        material = get_object_or_404(CourseMaterial, pk=serializer.validated_data['material'].pk)
        self._check_material_owner(material, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        self._check_material_owner(obj.material, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_material_owner(instance.material, self.request.user)
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


class TranscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = TranscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Transcription.objects.select_related('material__course', 'material__course__owner').all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)

        user = self.request.user
        if user.role == 'etudiant':
            qs = qs.filter(material__course__status='published')
        elif user.role == 'professeur':
            qs = qs.filter(Q(material__course__owner=user) | Q(material__course__status='published'))
        elif not user.role:
            qs = qs.none()
        return qs.distinct()

    def _check_material_owner(self, material, user):
        if material.course.owner != user and not user.is_superuser:
            raise PermissionDenied("Non autorisé sur ce matériel.")

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        material = get_object_or_404(CourseMaterial, pk=serializer.validated_data['material'].pk)
        self._check_material_owner(material, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        self._check_material_owner(obj.material, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_material_owner(instance.material, self.request.user)
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


class SummaryViewSet(viewsets.ModelViewSet):
    serializer_class = SummarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Summary.objects.select_related('material__course', 'material__course__owner').all()
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)

        user = self.request.user
        if user.role == 'etudiant':
            qs = qs.filter(material__course__status='published')
        elif user.role == 'professeur':
            qs = qs.filter(Q(material__course__owner=user) | Q(material__course__status='published'))
        elif not user.role:
            qs = qs.none()
        return qs.distinct()

    def _check_material_owner(self, material, user):
        if material.course.owner != user and not user.is_superuser:
            raise PermissionDenied("Non autorisé sur ce matériel.")

    def perform_create(self, serializer):
        _require_professor_or_admin(self.request.user)
        material = get_object_or_404(CourseMaterial, pk=serializer.validated_data['material'].pk)
        self._check_material_owner(material, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        self._check_material_owner(obj.material, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_material_owner(instance.material, self.request.user)
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



class LessonCompletionViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste les supports compl\u00e9t\u00e9s par l'utilisateur connect\u00e9 (gating des quiz)."""
    serializer_class = LessonCompletionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LessonCompletion.objects.filter(user=self.request.user).select_related('material')
