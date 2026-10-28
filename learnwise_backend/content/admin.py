from django.contrib import admin
from .models import Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial, VideoMaterial, Transcription, Summary, CoursePresence, CourseVersion, CoursePrerequisite, Badge


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


@admin.register(CoursePresence)
class CoursePresenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'joined_at', 'last_seen']
    list_filter = ['course', 'joined_at', 'last_seen']
    search_fields = ['user__email', 'course__title']
    readonly_fields = ['channel_name']


@admin.register(CourseVersion)
class CourseVersionAdmin(admin.ModelAdmin):
    list_display = ['course', 'version_number', 'change_description', 'created_by', 'created_at']
    list_filter = ['course', 'created_at', 'created_by']
    search_fields = ['course__title', 'change_description', 'created_by__email']
    readonly_fields = ['snapshot']


@admin.register(CoursePrerequisite)
class CoursePrerequisiteAdmin(admin.ModelAdmin):
    list_display = ['course', 'prerequisite_course', 'created_at']
    list_filter = ['course', 'prerequisite_course', 'created_at']
    search_fields = ['course__title', 'prerequisite_course__title']


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'course', 'awarded_at']
    list_filter = ['course', 'awarded_at']
    search_fields = ['name', 'user__email', 'course__title']
    readonly_fields = ['awarded_at', 'created_at']
