from django.core.management.base import BaseCommand
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.db import models
from datetime import timedelta
from content.models import Course, CourseMaterial
from accounts.models import User, UserSession


class Command(BaseCommand):
    help = 'Send reminder emails to students who have not completed their courses'

    def handle(self, *args, **options):
        self.stdout.write('Starting course completion reminders...')

        now = timezone.now()
        one_week_ago = now - timedelta(days=7)

        courses = Course.objects.filter(status='published')

        for course in courses:
            # Get all materials in the course
            all_materials = CourseMaterial.objects.filter(
                models.Q(course=course) | models.Q(chapter__course=course)
            ).distinct()
            total = all_materials.count()

            if total == 0:
                continue

            # Get users who had recent activity
            recent_sessions = UserSession.objects.filter(
                created_at__gt=one_week_ago
            ).values('user').distinct()

            for session_user_id in recent_sessions:
                user = User.objects.get(pk=session_user_id['user'])

                # Count accessed materials for this user
                # We count UserSession entries as an indicator of activity
                accessed = UserSession.objects.filter(user=user).count()

                # Consider course complete if user has significant activity
                is_complete = accessed >= total * 0.5  # 50% threshold

                if not is_complete:
                    context = {
                        'user': user,
                        'course': course,
                        'completed': accessed,
                        'total': total,
                    }

                    html_message = render_to_string('emails/course_reminder.html', context)

                    send_mail(
                        subject=f'Remember: Continue {course.title}',
                        message='',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message,
                    )
                    self.stdout.write(f'Reminder sent to {user.email} for course {course.title}')

        self.stdout.write('Reminders complete.')