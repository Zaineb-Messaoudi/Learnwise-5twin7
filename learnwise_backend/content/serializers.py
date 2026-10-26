from rest_framework import serializers
from .models import Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial, VideoMaterial, Transcription, Summary


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

    class Meta:
        model = CourseMaterial
        fields = [
            'id', 'course', 'course_title', 'chapter', 'chapter_title',
            'title', 'file', 'file_url', 'material_type',
            'file_size', 'file_size_mb', 'uploaded_at',
        ]
        read_only_fields = ['id', 'course_title', 'chapter_title', 'file_url', 'file_size', 'file_size_mb', 'uploaded_at']

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
