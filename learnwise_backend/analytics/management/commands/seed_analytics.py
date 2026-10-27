from datetime import timedelta
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import Enrollment, LearningActivity, LearningPath, LearningSession, Performance, Progress
from analytics.services import evaluate_achievements

class Command(BaseCommand):
    help = "Create idempotent demonstration data for learning analytics."
    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo.student@learnwise.local")
    def handle(self, *args, **options):
        user, _ = get_user_model().objects.get_or_create(
            email=options["email"], defaults={"username": "analytics-demo", "role": "etudiant", "email_verified": True}
        )
        course, _ = apps.get_model("content", "Course").objects.get_or_create(
            title="Fondamentaux de l'IA", defaults={"description": "Cours de démonstration", "level": "beginner", "language": "fr"}
        )
        path, _ = LearningPath.objects.get_or_create(user=user, title="Parcours IA", defaults={"description": "Votre parcours personnalisé."})
        Enrollment.objects.update_or_create(user=user, course=course, defaults={"learning_path": path, "status": "active"})
        Progress.objects.update_or_create(user=user, course=course, defaults={"completion_percentage": 65})
        Performance.objects.update_or_create(user=user, course=course, defaults={"average_score": 82, "quiz_count": 3, "exercise_count": 2})
        for day in range(5):
            started = timezone.now() - timedelta(days=day, minutes=35)
            session, _ = LearningSession.objects.get_or_create(user=user, course=course, started_at=started,
                                                               defaults={"ended_at": started + timedelta(minutes=35), "duration": 2100})
            LearningActivity.objects.get_or_create(session=session, activity_type="course_view", started_at=started)
        evaluate_achievements(user)
        self.stdout.write(self.style.SUCCESS(f"Analytics demo ready for {user.email}"))
