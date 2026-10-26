from django.contrib import admin
from .models import Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial, VideoMaterial, Transcription, Summary


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'level', 'language', 'owner', 'created_at']
    list_filter = ['status', 'level', 'language', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'materials_count', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'course__title']
    ordering = ['course', 'order']

    def materials_count(self, obj):
        return obj.materials.count()
    materials_count.short_description = 'Matériaux'


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'chapter', 'material_type', 'file_size', 'uploaded_at']
    list_filter = ['material_type', 'uploaded_at', 'chapter']
    search_fields = ['title', 'course__title', 'chapter__title']
    ordering = ['-uploaded_at']


@admin.register(AudioMaterial)
class AudioMaterialAdmin(admin.ModelAdmin):
    list_display = ['material', 'duration', 'language']
    list_filter = ['language']


@admin.register(DocumentMaterial)
class DocumentMaterialAdmin(admin.ModelAdmin):
    list_display = ['material', 'page_count', 'mime_type']


@admin.register(VideoMaterial)
class VideoMaterialAdmin(admin.ModelAdmin):
    list_display = ['material', 'duration', 'resolution', 'language']
    list_filter = ['language', 'resolution']


@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    list_display = ['material', 'language', 'created_at']
    list_filter = ['language', 'created_at']
    search_fields = ['content']


@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ['material', 'summary_type', 'created_at']
    list_filter = ['summary_type', 'created_at']
    search_fields = ['content']
