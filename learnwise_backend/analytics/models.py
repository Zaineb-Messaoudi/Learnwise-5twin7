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
    reference_id = models.UUIDField(null=True, blank=True)
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


class Cohort(UUIDModel):
    """A real class/group used as the comparison population."""
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True, default="")
    course = models.ForeignKey("content.Course", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="analytics_cohorts")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class CohortMembership(UUIDModel):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="analytics_cohort_memberships")
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("cohort", "user"), name="analytics_unique_cohort_member")]
        indexes = [models.Index(fields=("cohort", "user"), name="an_cohort_member")]


class Concept(UUIDModel):
    """A curriculum notion/objective, explicitly attached to a course."""
    course = models.ForeignKey("content.Course", on_delete=models.CASCADE, related_name="analytics_concepts")
    code = models.CharField(max_length=80)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("course_id", "code")
        constraints = [models.UniqueConstraint(fields=("course", "code"), name="analytics_unique_course_concept")]

    def __str__(self):
        return f"{self.course}: {self.title}"


class QuestionConcept(UUIDModel):
    """Decoupled mapping to assessment.Question (whose PK is currently integer)."""
    question_id = models.PositiveBigIntegerField()
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="question_mappings")
    weight = models.FloatField(default=1, validators=(MinValueValidator(0.01),))

    class Meta:
        constraints = [models.UniqueConstraint(fields=("question_id", "concept"), name="analytics_unique_question_concept")]
        indexes = [models.Index(fields=("question_id",), name="an_question_id")]


class WeeklyLearningSnapshot(UUIDModel):
    """Immutable weekly feature vector derived only from recorded activity."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="learning_radar_snapshots")
    course = models.ForeignKey("content.Course", on_delete=models.CASCADE,
                               related_name="learning_radar_snapshots")
    week_start = models.DateField()
    learning_seconds = models.PositiveIntegerField(default=0)
    session_count = models.PositiveIntegerField(default=0)
    completed_session_count = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(null=True, blank=True)
    assessment_count = models.PositiveIntegerField(default=0)
    completion_percentage = models.FloatField(default=0)
    concept_error_rate = models.FloatField(null=True, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-week_start",)
        constraints = [models.UniqueConstraint(fields=("user", "course", "week_start"),
                                                   name="analytics_unique_weekly_snapshot")]
        indexes = [models.Index(fields=("user", "course", "week_start"), name="an_snapshot_user_course")]


class LearningRisk(UUIDModel):
    class Level(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="learning_risks")
    course = models.ForeignKey("content.Course", on_delete=models.CASCADE,
                               related_name="learning_risks")
    risk_level = models.CharField(max_length=10, choices=Level.choices)
    risk_score = models.FloatField(validators=(MinValueValidator(0), MaxValueValidator(1)))
    confidence = models.CharField(max_length=10, choices=Level.choices, default=Level.LOW)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    evidence = models.JSONField(default=list)
    model_version = models.CharField(max_length=40, default="rules-v1")
    detected_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-detected_at",)
        indexes = [models.Index(fields=("user", "course", "status"), name="an_risk_user_course")]


class Intervention(UUIDModel):
    class Action(models.TextChoices):
        RESUME_COURSE = "resume_course", "Resume course"
        REVIEW_CONCEPT = "review_concept", "Review concept"
        TAKE_QUIZ = "take_quiz", "Take quiz"
        SHORT_SESSION = "short_session", "Short study session"

    risk = models.ForeignKey(LearningRisk, on_delete=models.CASCADE, related_name="interventions")
    action_type = models.CharField(max_length=30, choices=Action.choices)
    title = models.CharField(max_length=255)
    reason = models.TextField()
    priority = models.PositiveSmallIntegerField(default=1)
    estimated_minutes = models.PositiveSmallIntegerField(default=15)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("priority", "created_at")
