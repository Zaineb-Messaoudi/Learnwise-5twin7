from django.contrib import admin

from .models import (
    AssistantMessage,
    AssistantSession,
    Explanation,
    Illustration,
    VoiceQuestion,
)


class VoiceQuestionInline(admin.TabularInline):
    model = VoiceQuestion
    extra = 0
    fields = ('audio_file', 'transcription', 'status')


class AssistantMessageInline(admin.TabularInline):
    model = AssistantMessage
    extra = 0
    fields = ('role', 'content', 'status')


@admin.register(AssistantSession)
class AssistantSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'course', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('title', 'user__email')
    inlines = [VoiceQuestionInline, AssistantMessageInline]


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'status', 'created_at')
    list_filter = ('role', 'status')


@admin.register(VoiceQuestion)
class VoiceQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'status', 'created_at')
    list_filter = ('status',)


admin.site.register([Explanation, Illustration])
