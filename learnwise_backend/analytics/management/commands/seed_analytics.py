from datetime import timedelta
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import (Concept, Enrollment, LearningActivity, LearningPath, LearningSession,
                              Performance, Progress, QuestionConcept)
from analytics.services import evaluate_achievements

class Command(BaseCommand):
    help = "Create idempotent demonstration data for learning analytics."
    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo.student@learnwise.local")
        parser.add_argument("--password", default="Learnwise-Demo-2026!")
    def handle(self, *args, **options):
        user, _ = get_user_model().objects.get_or_create(
            email=options["email"], defaults={"username": "analytics-demo", "role": "etudiant", "email_verified": True}
        )
        user.set_password(options["password"])
        user.role = "etudiant"
        user.email_verified = True
        user.save(update_fields=("password", "role", "email_verified"))
        # Mark demo onboarding as complete so the account can open the React
        # dashboard without requiring a real webcam enrollment.
        apps.get_model("accounts", "FaceProfile").objects.update_or_create(
            user=user,
            defaults={"descriptor": [0.0] * 128, "is_verified": True},
        )
        course, _ = apps.get_model("content", "Course").objects.get_or_create(
            title="Fondamentaux de l'IA", defaults={"description": "Cours de démonstration", "level": "beginner", "language": "fr"}
        )
        path, _ = LearningPath.objects.get_or_create(user=user, title="Parcours IA", defaults={"description": "Votre parcours personnalisé."})
        Enrollment.objects.update_or_create(user=user, course=course, defaults={"learning_path": path, "status": "active"})
        Progress.objects.update_or_create(user=user, course=course, defaults={
            "completion_percentage": 65,
            "last_activity": timezone.now() - timedelta(days=10),
        })
        Quiz = apps.get_model("assessment", "Quiz")
        Question = apps.get_model("assessment", "Question")
        QuizAttempt = apps.get_model("assessment", "QuizAttempt")
        Answer = apps.get_model("assessment", "Answer")
        Evaluation = apps.get_model("assessment", "Evaluation")
        quiz, _ = Quiz.objects.get_or_create(title="Diagnostic IA", defaults={"description": "Quiz de démonstration", "difficulty": "medium"})
        question, _ = Question.objects.get_or_create(quiz=quiz, text="Quel est le rôle d'un modèle ?",
                                                     defaults={"type": "qcm", "difficulty": "medium"})
        concept, _ = Concept.objects.get_or_create(course=course, code="modeles-ia",
                                                   defaults={"title": "Modèles d'IA", "description": "Notion de démonstration"})
        QuestionConcept.objects.get_or_create(question_id=question.pk, concept=concept)
        attempt = QuizAttempt.objects.filter(user=user, quiz=quiz).first() or QuizAttempt.objects.create(user=user, quiz=quiz)
        Answer.objects.update_or_create(attempt=attempt, question=question, defaults={"is_correct": True})
        Evaluation.objects.update_or_create(attempt=attempt, defaults={"score": 82, "feedback": "Évaluation de démonstration"})
        Performance.objects.filter(user=user, course=course).update(exercise_count=0)
        for day in range(5):
            started = timezone.now() - timedelta(days=day, minutes=35)
            session, _ = LearningSession.objects.get_or_create(user=user, course=course, started_at=started,
                                                               defaults={"ended_at": started + timedelta(minutes=35), "duration": 2100})
            LearningActivity.objects.get_or_create(session=session, activity_type="course_view", started_at=started)
        evaluate_achievements(user)
        # Deliberately stale demo signal so Learning Radar is visible in the UI.
        Progress.objects.filter(user=user, course=course).update(last_activity=timezone.now() - timedelta(days=10))
        from analytics.radar import evaluate_course_risk
        evaluate_course_risk(user, course)
        self.stdout.write(self.style.SUCCESS(f"Analytics demo ready for {user.email}"))
        self.stdout.write("Use the --password value to sign in; this command is for local/demo data only.")
