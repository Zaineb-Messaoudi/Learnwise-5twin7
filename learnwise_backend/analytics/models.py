"""Persistence models for the learning analytics bounded context."""
import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta:
        abstract = True

class LearningPath(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_paths")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    class Meta:
        ordering = ("-created_at",)
    def __str__(self):
        return f"{self.title} - {self.user.email}"

class Enrollment(UUIDModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        DROPPED = "dropped", "Dropped"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey("content.Course", on_delete=models.CASCADE, related_name="enrollments")
    learning_path = models.ForeignKey(LearningPath, null=True, blank=True, on_delete=models.SET_NULL, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    class Meta:
        ordering = ("-enrolled_at",)
        constraints = [models.UniqueConstraint(fields=("user", "course"), name="analytics_unique_enrollment")]
        indexes = [models.Index(fields=("user", "course"), name="analytics_enroll_user_course")]
    def __str__(self):
        return f"{self.user.email} in {self.course.title}"

class LearningSession(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_sessions")
    course = models.ForeignKey("content.Course", on_delete=models.CASCADE, related_name="learning_sessions")
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    class Meta:
        ordering = ("-started_at",)
        indexes = [models.Index(fields=("user", "course"), name="analytics_session_user_course")]
    def end(self, at=None):
        self.ended_at = at or timezone.now()
        self.duration = max(0, int((self.ended_at - self.started_at).total_seconds()))
        self.save(update_fields=("ended_at", "duration"))
    def __str__(self):
        return f"Session {self.pk} - {self.course.title}"

class LearningActivity(UUIDModel):
    class Type(models.TextChoices):
        COURSE_VIEW = "course_view", "Course view"
        LESSON_STARTED = "lesson_started", "Lesson started"
        LESSON_COMPLETED = "lesson_completed", "Lesson completed"
        QUIZ = "quiz", "Quiz"
        EXERCISE = "exercise", "Exercise"
        VOICE_QUESTION = "voice_question", "Voice question"
    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=40, choices=Type.choices)
    material = models.ForeignKey(
        "content.CourseMaterial", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="learning_activities",
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ("-started_at",)
        indexes = [models.Index(fields=("session", "activity_type"), name="an_activity_session_type")]
    def __str__(self):
        return f"{self.activity_type} in {self.session_id}"

class Progress(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress_records")
    course = models.ForeignKey("content.Course", on_delete=models.CASCADE, related_name="progress")
    completion_percentage = models.FloatField(default=0, validators=(MinValueValidator(0), MaxValueValidator(100)))
    last_activity = models.DateTimeField(default=timezone.now)
    class Meta:
        ordering = ("-last_activity",)
        constraints = [models.UniqueConstraint(fields=("user", "course"), name="analytics_unique_progress")]
        indexes = [models.Index(fields=("user", "course"), name="analytics_progress_user_course")]
    def __str__(self):
        return f"{self.user.email}: {self.course.title} ({self.completion_percentage:.0f}%)"

class Performance(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="performance_records")
    course = models.ForeignKey("content.Course", on_delete=models.CASCADE, related_name="performance")
    average_score = models.FloatField(default=0, validators=(MinValueValidator(0), MaxValueValidator(100)))
    quiz_count = models.PositiveIntegerField(default=0)
    exercise_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ("-updated_at",)
        constraints = [models.UniqueConstraint(fields=("user", "course"), name="analytics_unique_performance")]
        indexes = [models.Index(fields=("user", "course"), name="analytics_perf_user_course")]
    def __str__(self):
        return f"{self.user.email}: {self.course.title} ({self.average_score:.1f})"

class Achievement(UUIDModel):
    class Code(models.TextChoices):
        LEGACY = "legacy", "Legacy achievement"
        FIRST_QUIZ = "first_quiz", "First quiz"
        FIVE_SESSIONS = "five_sessions", "Five sessions"
        COURSE_COMPLETE = "course_complete", "Course complete"
        HIGH_SCORE = "high_score", "High score"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    code = models.CharField(max_length=40, choices=Code.choices, default=Code.LEGACY)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    earned_at = models.DateTimeField(default=timezone.now)
    class Meta:
        ordering = ("-earned_at",)
        constraints = [models.UniqueConstraint(fields=("user", "code"), name="analytics_unique_achievement")]
        indexes = [models.Index(fields=("user", "earned_at"), name="an_achievement_user_date")]
    def __str__(self):
        return f"{self.title} - {self.user.email}"
