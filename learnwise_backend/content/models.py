import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


def upload_to_course_material(instance, filename):
    ext = filename.split('.')[-1] if '.' in filename else ''
    return f"course_materials/{timezone.now().strftime('%Y/%m/%d')}/{uuid.uuid4().hex}.{ext}"


class Course(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
        ('archived', 'Archivé'),
    ]
    CONTENT_TYPE_CHOICES = [
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Vidéo'),
        ('code', 'Code'),
        ('markdown', 'Markdown'),
        ('latex', 'LaTeX'),
        ('mixed', 'Mixte'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=50, default='fr')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='document')
    markdown_content = models.TextField(blank=True, help_text="Contenu du cours en Markdown")
    latex_content = models.TextField(blank=True, help_text="Contenu du cours en LaTeX")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_created', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'owner']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['content_type']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Chapter(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text="Ordre d'affichage du chapitre dans le cours")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['course', 'order']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class CourseMaterial(models.Model):
    MATERIAL_TYPE_CHOICES = [
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Vidéo'),
        ('code', 'Code'),
        ('other', 'Autre'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='materials', null=True, blank=True, help_text="Chapitre auquel appartient ce support (vide = support de cours général)")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_to_course_material, blank=True, null=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES, default='other')
    file_size = models.BigIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['course', 'material_type']),
            models.Index(fields=['chapter']),
        ]

    def __str__(self):
        chapter_label = f"[{self.chapter.title}]" if self.chapter else "[Cours]"
        return f"{chapter_label} {self.title}"


class AudioMaterial(models.Model):
    material = models.OneToOneField(CourseMaterial, on_delete=models.CASCADE, related_name='audio_details')
    duration = models.IntegerField(help_text="Durée en secondes", null=True, blank=True)
    language = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Audio pour {self.material.title}"


class DocumentMaterial(models.Model):
    material = models.OneToOneField(CourseMaterial, on_delete=models.CASCADE, related_name='document_details')
    page_count = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Document pour {self.material.title}"


class VideoMaterial(models.Model):
    material = models.OneToOneField(CourseMaterial, on_delete=models.CASCADE, related_name='video_details')
    duration = models.IntegerField(help_text="Durée en secondes", null=True, blank=True)
    resolution = models.CharField(max_length=20, blank=True, help_text="Ex: 1920x1080")
    language = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Vidéo pour {self.material.title}"


class Transcription(models.Model):
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='transcriptions')
    content = models.TextField(blank=True)
    language = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Transcription pour {self.material.title}"


class Summary(models.Model):
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='summaries')
    content = models.TextField(blank=True)
    summary_type = models.CharField(max_length=50, default='general')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Résumé pour {self.material.title}"
