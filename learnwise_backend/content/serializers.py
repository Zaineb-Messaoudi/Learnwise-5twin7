from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial, VideoMaterial, Transcription, Summary, CoursePresence, CourseVersion, CoursePrerequisite, LessonCompletion


class ChapterSerializer(serializers.ModelSerializer):
    materials_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'course', 'title', 'description', 'order', 'materials_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'materials_count', 'created_at', 'updated_at']

    def get_materials_count(self, obj):
        return obj.materials.count()


class CourseSerializer(serializers.ModelSerializer):
    owner_email = serializers.SerializerMethodField(read_only=True)
    materials_count = serializers.SerializerMethodField(read_only=True)
    chapters_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'level', 'language',
            'status', 'content_type', 'markdown_content', 'latex_content',
            'owner', 'owner_email', 'materials_count', 'chapters_count',
            'scheduled_publish_at', 'estimated_reading_minutes', 'slug',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'owner_email', 'materials_count', 'chapters_count', 'created_at', 'updated_at']

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner else None

    def get_materials_count(self, obj):
        return obj.materials.count()

    def get_chapters_count(self, obj):
        return obj.chapters.count()


class CourseMaterialSerializer(serializers.ModelSerializer):
    course_title = serializers.SerializerMethodField(read_only=True)
    chapter_title = serializers.SerializerMethodField(read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)
    file_size_mb = serializers.SerializerMethodField(read_only=True)
    thumbnail_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseMaterial
        fields = [
            'id', 'course', 'course_title', 'chapter', 'chapter_title',
            'title', 'file', 'file_url', 'thumbnail_url', 'material_type',
            'file_size', 'file_size_mb', 'uploaded_at',
        ]
        read_only_fields = ['id', 'course_title', 'chapter_title', 'file_url', 'thumbnail_url', 'file_size', 'file_size_mb', 'uploaded_at']

    def get_course_title(self, obj):
        return obj.course.title if obj.course else None

    def get_chapter_title(self, obj):
        return obj.chapter.title if obj.chapter else None

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None

    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
        return None

    def validate_file(self, value):
        if not value:
            return value
        # Enforce max upload size
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 100 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(f'File too large. Maximum size is {max_size // (1024 * 1024)}MB.')
        # Enforce allowed extensions
        allowed = getattr(settings, 'ALLOWED_MATERIAL_EXTENSIONS', [])
        if allowed:
            import os
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in allowed:
                raise serializers.ValidationError(f'File extension "{ext}" is not allowed. Allowed: {", ".join(allowed)}')
        return value


class AudioMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioMaterial
        fields = ['id', 'material', 'duration', 'language']
        read_only_fields = ['id']


class DocumentMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentMaterial
        fields = ['id', 'material', 'page_count', 'mime_type']
        read_only_fields = ['id']


class VideoMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoMaterial
        fields = ['id', 'material', 'duration', 'resolution', 'language']
        read_only_fields = ['id']


class TranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = ['id', 'material', 'content', 'language', 'created_at']
        read_only_fields = ['id', 'created_at']


class SummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = ['id', 'material', 'content', 'summary_type', 'created_at']
        read_only_fields = ['id', 'created_at']


class CourseVersionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseVersion
        fields = [
            'id', 'course', 'version_number', 'snapshot',
            'change_description', 'created_by', 'created_by_email', 'created_at',
        ]
        read_only_fields = ['id', 'course', 'version_number', 'snapshot', 'created_by', 'created_by_email', 'created_at']

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None


class CoursePrerequisiteSerializer(serializers.ModelSerializer):
    prerequisite_title = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CoursePrerequisite
        fields = ['id', 'course', 'prerequisite_course', 'prerequisite_title', 'created_at']
        read_only_fields = ['id', 'course', 'created_at']

    def get_prerequisite_title(self, obj):
        return obj.prerequisite_course.title if obj.prerequisite_course else None

    def create(self, validated_data):
        # course is set from the view context (URL pk), not from request data
        instance = CoursePrerequisite(**validated_data)
        instance.full_clean()  # runs clean() for circular dependency check
        instance.save()
        return instance


class LessonCompletionSerializer(serializers.ModelSerializer):
    """Serializer for a user's completed lesson materials (quiz gating)."""
    material_id = serializers.SerializerMethodField()
    material_title = serializers.SerializerMethodField()
    material_kind = serializers.SerializerMethodField()

    class Meta:
        model = LessonCompletion
        fields = ['id', 'material_id', 'material_title', 'material_kind', 'completed_at']
        read_only_fields = ['id', 'material_id', 'material_title', 'material_kind', 'completed_at']

    def get_material_id(self, obj):
        return obj.material_id

    def get_material_title(self, obj):
        return obj.material.title

    def get_material_kind(self, obj):
        return obj.material.material_type
