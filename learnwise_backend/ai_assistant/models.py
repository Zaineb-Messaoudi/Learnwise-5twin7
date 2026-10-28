from django.conf import settings
from django.db import models
from django.utils import timezone


class ProcessingStatus(models.TextChoices):
    QUEUED = 'queued', 'Queued'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class AssistantSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assistant_sessions',
    )
    course = models.ForeignKey(
        'content.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assistant_sessions',
    )
    title = models.CharField(max_length=200, blank=True, default='')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return f"Session {self.pk} - {self.user}"


class VoiceQuestion(models.Model):
    session = models.ForeignKey(
        AssistantSession, on_delete=models.CASCADE, related_name='voice_questions'
    )
    audio_file = models.FileField(upload_to='voice_questions/')
    language = models.CharField(max_length=10, blank=True, default='')
    transcription = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.QUEUED,
    )
    progress = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=50, blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"Voice question {self.pk} (session {self.session_id})"


class AssistantMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    session = models.ForeignKey(
        AssistantSession, on_delete=models.CASCADE, related_name='messages'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    content = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.COMPLETED,
    )
    citations = models.JSONField(default=list, blank=True)
    error_code = models.CharField(max_length=50, blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"{self.role} message {self.pk} (session {self.session_id})"


class Explanation(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'

    message = models.ForeignKey(
        AssistantMessage, on_delete=models.CASCADE, related_name='explanations'
    )
    content = models.TextField()
    difficulty_level = models.CharField(
        max_length=20, choices=Difficulty.choices, default=Difficulty.INTERMEDIATE
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"Explanation ({self.difficulty_level}) for message {self.message_id}"


class Illustration(models.Model):
    message = models.ForeignKey(
        AssistantMessage, on_delete=models.CASCADE, related_name='illustrations'
    )
    prompt = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='assistant_illustrations/', blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.QUEUED,
    )
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"Illustration {self.pk} for message {self.message_id}"
