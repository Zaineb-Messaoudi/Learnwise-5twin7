from django.core.management.base import BaseCommand
from analytics.models import Enrollment
from analytics.radar import evaluate_course_risk

class Command(BaseCommand):
    help = "Build current snapshots and evaluate Learning Radar risks."
    def handle(self, *args, **options):
        evaluated = risks = 0
        enrollments = Enrollment.objects.exclude(status=Enrollment.Status.DROPPED).select_related("user", "course")
        for enrollment in enrollments.iterator():
            evaluated += 1
            risks += bool(evaluate_course_risk(enrollment.user, enrollment.course))
        self.stdout.write(self.style.SUCCESS(f"Learning Radar evaluated {evaluated} enrollments; {risks} open risks."))
