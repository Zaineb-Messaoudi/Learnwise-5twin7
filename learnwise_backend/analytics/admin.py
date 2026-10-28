from django.contrib import admin
from .models import (Achievement, Cohort, CohortMembership, Concept, Enrollment, Intervention,
                     LearningActivity, LearningPath, LearningRisk, LearningSession, Performance,
                     Progress, QuestionConcept, WeeklyLearningSnapshot)

@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at")
    search_fields = ("title", "user__email")

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "status", "enrolled_at")
    list_filter = ("status",)
    list_select_related = ("user", "course")

@admin.register(LearningSession)
class LearningSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "started_at", "ended_at", "duration")
    list_select_related = ("user", "course")

@admin.register(LearningActivity)
class LearningActivityAdmin(admin.ModelAdmin):
    list_display = ("activity_type", "session", "started_at", "completed_at")
    list_filter = ("activity_type",)

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "completion_percentage", "last_activity")
    list_select_related = ("user", "course")

@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "average_score", "quiz_count", "exercise_count")
    list_select_related = ("user", "course")

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "code", "earned_at")
    list_filter = ("code",)

admin.site.register(Cohort)
admin.site.register(CohortMembership)
admin.site.register(Concept)
admin.site.register(QuestionConcept)
admin.site.register(WeeklyLearningSnapshot)
admin.site.register(LearningRisk)
admin.site.register(Intervention)
