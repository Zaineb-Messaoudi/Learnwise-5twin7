import logging
import uuid
from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)


def upload_to_course_material(instance, filename):
    ext = filename.split('.')[-1] if '.' in filename else ''
    return f"course_materials/{timezone.now().strftime('%Y/%m/%d')}/{uuid.uuid4().hex}.{ext}"


class Course(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending_review', 'En attente de révision'),
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
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='courses_created', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    scheduled_publish_at = models.DateTimeField(null=True, blank=True, help_text="Date de publication planifiée. Si définie, le cours sera publié automatiquement à cette date.")
    estimated_reading_minutes = models.IntegerField(null=True, blank=True, help_text="Temps de lecture estimé en minutes (calculé automatiquement)")
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="Identifiant URL automatiquement généré depuis le titre")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'owner']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['content_type']),
            models.Index(fields=['scheduled_publish_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
            # Auto-publish if scheduled_publish_at is in the past (new course only;
            # updates must not override a manual status change such as reject/rollback)
            if self.scheduled_publish_at and timezone.now() >= self.scheduled_publish_at:
                if self.status == 'draft':
                    self.status = 'published'
        self.updated_at = timezone.now()
        # Auto-calculate estimated reading minutes
        self.estimated_reading_minutes = self._calculate_reading_time()
        # Auto-generate slug from title if not set
        if not self.slug:
            base_slug = slugify(self.title) or 'course'
            self.slug = base_slug
            counter = 1
            while Course.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def _calculate_reading_time(self):
        """Estimate reading time in minutes based on content."""
        import re
        words_per_minute = 200
        total_words = 0

        # Count words in description and markdown content
        for text in [self.description or '', self.markdown_content or '']:
            # Remove markdown syntax for rough word count
            clean = re.sub(r'[#*`\[\]()!_]', '', text)
            clean = re.sub(r'\s+', ' ', clean).strip()
            if clean:
                total_words += len(clean.split())

        # Add time for audio/video materials (average 2 min per material if duration unknown)
        try:
            audio_count = self.materials.filter(material_type='audio').count()
            video_count = self.materials.filter(material_type='video').count()
            total_words += (audio_count + video_count) * 200  # ~1 min each
        except Exception:
            pass

        minutes = max(1, round(total_words / words_per_minute))
        return minutes

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
    thumbnail = models.ImageField(upload_to='course_thumbnails/%Y/%m/%d/', blank=True, null=True, help_text="Miniature générée automatiquement")
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


class CoursePresence(models.Model):
    """Tracks users currently viewing a course (WebSocket presence)."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='presences')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_presences')
    channel_name = models.CharField(max_length=255)
    joined_at = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['course', 'user']),
            models.Index(fields=['channel_name']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['course', 'user'], name='unique_course_user_presence'),
        ]

    def __str__(self):
        return f"{self.user.email} on {self.course.title}"

    def touch(self):
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])


class CourseVersion(models.Model):
    """Immutable snapshot of a Course at a point in time, for rollback."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField(default=1)
    snapshot = models.JSONField(help_text="Serialized course data at this version")
    change_description = models.CharField(max_length=255, blank=True, help_text="Reason for this version")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_versions_created')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['course', 'version_number']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['course', 'version_number'], name='unique_course_version_number'),
        ]

    def __str__(self):
        return f"{self.course.title} v{self.version_number}"

    @classmethod
    def create_snapshot(cls, course, user, change_description=''):
        """Create a new version snapshot from the current course state."""
        last_version = cls.objects.filter(course=course).order_by('-version_number').first()
        next_version = (last_version.version_number + 1) if last_version else 1

        snapshot = {
            'title': course.title,
            'description': course.description,
            'level': course.level,
            'language': course.language,
            'status': course.status,
            'content_type': course.content_type,
            'markdown_content': course.markdown_content,
            'latex_content': course.latex_content,
        }

        return cls.objects.create(
            course=course,
            version_number=next_version,
            snapshot=snapshot,
            change_description=change_description,
            created_by=user,
        )

    def apply_to(self, course):
        """Apply this version's snapshot back to the course."""
        course.title = self.snapshot.get('title', course.title)
        course.description = self.snapshot.get('description', course.description)
        course.level = self.snapshot.get('level', course.level)
        course.language = self.snapshot.get('language', course.language)
        course.status = self.snapshot.get('status', course.status)
        course.content_type = self.snapshot.get('content_type', course.content_type)
        course.markdown_content = self.snapshot.get('markdown_content', course.markdown_content)
        course.latex_content = self.snapshot.get('latex_content', course.latex_content)
        course.save()
        return course


class CoursePrerequisite(models.Model):
    """A course that must be completed before another course can be accessed."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='prerequisites_for')
    prerequisite_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='is_prerequisite_for')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['course', 'prerequisite_course']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['course', 'prerequisite_course'], name='unique_course_prerequisite'),
            models.CheckConstraint(
                name='prerequisite_not_self',
                condition=~models.Q(course=models.F('prerequisite_course')),
            ),
        ]

    def __str__(self):
        return f"{self.prerequisite_course.title} → {self.course.title}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.course == self.prerequisite_course:
            raise ValidationError("Un cours ne peut pas être son propre prérequis.")
        # Check for circular dependencies
        if self._would_create_cycle():
            raise ValidationError("Ce prérequis créerait une dépendance circulaire.")

    def _would_create_cycle(self):
        """Check if adding this prerequisite would create a cycle.

        Starting from self.prerequisite_course, follow ALL existing "requires"
        chains (BFS). If we can reach self.course, adding course -> prerequisite_course
        closes the loop.
        """
        visited = set()
        queue = [self.prerequisite_course]
        while queue:
            current = queue.pop(0)
            if current.id == self.course.id:
                return True
            if current.id in visited:
                continue
            visited.add(current.id)
            # Follow ALL prerequisites of current, not just the first
            for prereq_rel in CoursePrerequisite.objects.filter(
                course=current
            ).select_related('prerequisite_course'):
                if prereq_rel.prerequisite_course.id not in visited:
                    queue.append(prereq_rel.prerequisite_course)
        return False

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


def badge_image_path(instance, filename):
    """Generate path for badge images: badges/course_{course_id}/"""
    ext = filename.split('.')[-1] if '.' in filename else 'png'
    return f'badges/course_{instance.course.id}/' + filename


class Badge(models.Model):
    """Awarded to users who complete a course."""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='badges',
        help_text="The course this badge is for."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='badges_earned',
        help_text="The user who earned this badge."
    )
    image = models.ImageField(
        upload_to=badge_image_path,
        help_text="Badge image (PNG, optimized for web)."
    )
    name = models.CharField(
        max_length=255,
        help_text="Display name of the badge (e.g., 'Course Completion')."
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the badge criteria."
    )
    criteria = models.JSONField(
        default=dict,
        help_text="JSON describing the criteria for earning the badge."
    )
    awarded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['course', 'user']
        ordering = ['-awarded_at']

    def __str__(self):
        return f"{self.name} - {self.user.email} on {self.course.title}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('course-detail', args=[self.course.id])


def check_course_completion(course, user):
    """Check if a user has completed all materials in a course.
    
    A course is considered complete when the user has viewed/accessed all
    materials associated with the course (including materials in chapters).
    """
    from content.models import CourseMaterial
    
    # Get all materials in the course (including those in chapters)
    all_materials = CourseMaterial.objects.filter(
        models.Q(course=course) | models.Q(chapter__course=course)
    ).distinct()
    
    total_materials = all_materials.count()
    if total_materials == 0:
        return False, 0
    
    # Check user's progress - materials they've accessed via ActivityLog
    from accounts.models import ActivityLog
    accessed_materials = ActivityLog.objects.filter(
        user=user,
        resource_type='material',
        resource_id__in=[str(m.id) for m in all_materials]
    ).values('resource_id').distinct()
    
    accessed_ids = set(s['resource_id'] for s in accessed_materials)
    completed_count = len(accessed_ids)
    
    is_complete = completed_count >= total_materials
    
    return is_complete, completed_count


def send_course_reminders():
    """Send reminder emails to students who haven't completed their courses."""
    from django.conf import settings
    from datetime import timedelta
    from accounts.models import ActivityLog, User as CustomUser
    
    now = timezone.now()
    one_week_ago = now - timedelta(days=7)
    
    # Find courses with enrollments
    courses = Course.objects.filter(status='published')
    
    for course in courses:
        # Get students who accessed this course recently via ActivityLog
        enrolled_users = ActivityLog.objects.filter(
            user__isnull=False,
            resource_type='course',
            resource_id=str(course.id),
            created_at__gt=one_week_ago
        ).values('user').distinct()
        
        for session in enrolled_users:
            try:
                user = CustomUser.objects.get(pk=session['user'])
            except CustomUser.DoesNotExist:
                continue
            
            # Skip users who don't have a role yet (not onboarded)
            if not user.role:
                continue
            
            # Check if user has completed this course
            is_complete, completed = check_course_completion(course, user)
            
            if not is_complete:
                total = CourseMaterial.objects.filter(
                    models.Q(course=course) | models.Q(chapter__course=course)
                ).distinct().count()
                
                subject = f'Remember: Continue {course.title}'
                message = f'''
Hello {user.first_name or user.email},

You recently started {course.title} but haven't finished it yet.
You have completed {completed} of {total} materials.

Keep learning at {settings.FRONTEND_URL}

Best regards,
The Learnwise Team
'''.strip()

                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                except Exception:
                    logger.exception('Failed to send course reminder to %s', user.email)