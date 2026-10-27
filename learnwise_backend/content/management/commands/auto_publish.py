from django.core.management.base import BaseCommand
from django.utils import timezone
from content.models import Course


class Command(BaseCommand):
    help = 'Publish courses whose scheduled_publish_at has passed.'

    def handle(self, *args, **options):
        now = timezone.now()
        courses = Course.objects.filter(
            status='draft',
            scheduled_publish_at__lte=now,
        )
        count = 0
        for course in courses:
            course.status = 'published'
            course.save(update_fields=['status', 'updated_at'])
            count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Published course "{course.title}" (id={course.id})')
            )
        if count == 0:
            self.stdout.write('No courses to publish.')
        else:
            self.stdout.write(self.style.SUCCESS(f'{count} course(s) published.'))
