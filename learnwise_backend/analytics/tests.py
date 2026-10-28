from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from content.models import Course, CourseMaterial, LessonCompletion
from .models import (Achievement, Cohort, CohortMembership, Concept, Enrollment, Intervention,
                     LearningActivity, LearningRisk, LearningSession, Performance, Progress,
                     QuestionConcept)
from .services import evaluate_achievements, recommendations_for
from learnwise_backend.asgi import application

class AnalyticsTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="student", email="student@example.com", password="secret", role="etudiant")
        self.other = get_user_model().objects.create_user(username="other", email="other@example.com", password="secret", role="etudiant")
        self.course = Course.objects.create(title="Django", description="API", level="beginner", language="fr", status="published")
        CourseMaterial.objects.create(
            course=self.course, title="Intro",
            file=SimpleUploadedFile("test.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf"),
            material_type="pdf",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
    def test_enrollment_is_scoped_and_creates_progress(self):
        response = self.client.post(reverse("enrollment-list"), {"course_id": self.course.pk}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Progress.objects.filter(user=self.user, course=self.course).exists())
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(reverse("enrollment-list")).data["count"], 0)
    def test_completed_activity_updates_progress_and_dashboard(self):
        session = LearningSession.objects.create(user=self.user, course=self.course)
        material = self.course.materials.first()
        LessonCompletion.objects.create(user=self.user, material=material)
        self.assertEqual(Progress.objects.get(user=self.user, course=self.course).completion_percentage, 100)
        response = self.client.get(reverse("analytics-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stats"]["achievement_count"], 1)
    def test_badges_are_idempotent(self):
        for index in range(5):
            LearningSession.objects.create(user=self.user, course=self.course, ended_at=timezone.now(), duration=index + 1)
        evaluate_achievements(self.user)
        evaluate_achievements(self.user)
        self.assertEqual(Achievement.objects.filter(user=self.user, code="five_sessions").count(), 1)
    def test_inactive_course_recommendation(self):
        Progress.objects.create(user=self.user, course=self.course, completion_percentage=40,
                                last_activity=timezone.now() - timedelta(days=10))
        self.assertEqual(recommendations_for(self.user)[0]["type"], "inactive_course")

    def test_session_start_and_end_endpoints(self):
        start = self.client.post(reverse("session-start"), {"course_id": self.course.pk}, format="json")
        self.assertEqual(start.status_code, 201)
        finish = self.client.post(reverse("session-end", kwargs={"pk": start.data["id"]}), format="json")
        self.assertEqual(finish.status_code, 200)
        self.assertIsNotNone(finish.data["ended_at"])

    def test_analytics_websocket_accepts_jwt_and_receives_events(self):
        from rest_framework_simplejwt.tokens import AccessToken

        async def scenario():
            token = str(AccessToken.for_user(self.user))
            communicator = WebsocketCommunicator(application, f"/ws/analytics/?token={token}")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            self.assertEqual((await communicator.receive_json_from())["event"], "connected")
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_legacy_progress_websocket_uses_authenticated_user_not_url_id(self):
        from rest_framework_simplejwt.tokens import AccessToken

        async def scenario():
            token = str(AccessToken.for_user(self.user))
            communicator = WebsocketCommunicator(
                application, f"/ws/progress/{self.other.pk}/?token={token}"
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            self.assertEqual((await communicator.receive_json_from())["type"], "connected")
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_indicators_explain_persisted_values(self):
        Progress.objects.create(user=self.user, course=self.course, completion_percentage=40)
        Performance.objects.create(user=self.user, course=self.course, average_score=75, quiz_count=2)
        response = self.client.get(reverse("student-indicators"))
        self.assertEqual(response.status_code, 200)
        item = response.data["courses"][0]
        self.assertEqual(item["average_score"]["value"], 75)
        self.assertEqual(item["average_score"]["observations"], 2)
        self.assertIn("analytics.Performance", item["average_score"]["sources"])

    def test_weaknesses_use_mapped_real_answers(self):
        from assessment.models import Answer, Question, Quiz, QuizAttempt
        quiz = Quiz.objects.create(title="Quiz Django", description="", difficulty="easy")
        question = Question.objects.create(quiz=quiz, prompt="ORM", type="single_choice", difficulty="easy")
        concept = Concept.objects.create(course=self.course, code="orm", title="Django ORM")
        QuestionConcept.objects.create(question_id=question.pk, concept=concept)
        for correct in (False, True):
            attempt = QuizAttempt.objects.create(user=self.user, quiz=quiz)
            Answer.objects.create(attempt=attempt, question=question, is_correct=correct)
        response = self.client.get(reverse("student-weaknesses"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["concepts"][0]["answers"], 2)
        self.assertEqual(response.data["concepts"][0]["error_rate"], 50.0)

    def test_teacher_can_compare_declared_cohort(self):
        from assessment.models import Evaluation, Quiz, QuizAttempt
        teacher = get_user_model().objects.create_user(username="teacher", email="teacher@example.com",
                                                       password="secret", role="professeur")
        cohort = Cohort.objects.create(name="Classe A", subject="Django", course=self.course)
        CohortMembership.objects.create(cohort=cohort, user=self.user)
        Performance.objects.create(user=self.user, course=self.course, average_score=80, quiz_count=1)
        quiz = Quiz.objects.create(title="Évaluation ORM", description="", difficulty="easy")
        attempt = QuizAttempt.objects.create(user=self.user, quiz=quiz)
        Evaluation.objects.create(attempt=attempt, score=80, feedback="")
        self.client.force_authenticate(teacher)
        response = self.client.get(reverse("cohort-comparison", kwargs={"cohort_id": cohort.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["members"], 1)
        self.assertEqual(response.data["by_evaluation"][0]["average_score"], 80.0)

    def test_learning_radar_detects_inactivity_with_evidence(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        progress = Progress.objects.create(user=self.user, course=self.course, completion_percentage=40)
        Progress.objects.filter(pk=progress.pk).update(last_activity=timezone.now() - timedelta(days=10))
        response = self.client.post(reverse("learning-radar"), format="json")
        self.assertEqual(response.status_code, 200)
        risk = response.data["risks"][0]
        self.assertEqual(risk["evidence"][0]["signal"], "inactive_days")
        self.assertEqual(risk["evidence"][0]["value"], 10)
        self.assertTrue(risk["interventions"])

    def test_learning_radar_does_not_create_risk_without_signal(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        Progress.objects.create(user=self.user, course=self.course, completion_percentage=40)
        response = self.client.post(reverse("learning-radar"), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["risks"], [])

    def test_student_can_complete_own_intervention(self):
        risk = LearningRisk.objects.create(user=self.user, course=self.course, risk_level="medium", risk_score=.4,
                                           confidence="low", evidence=[])
        intervention = Intervention.objects.create(risk=risk, action_type="resume_course", title="Reprendre",
                                                   reason="Inactivité")
        response = self.client.post(reverse("complete-intervention", kwargs={"intervention_id": intervention.pk}))
        self.assertEqual(response.status_code, 200)
        intervention.refresh_from_db()
        self.assertIsNotNone(intervention.completed_at)

    def test_performance_is_recomputed_from_real_evaluations(self):
        from assessment.models import Evaluation, Question, Quiz, QuizAttempt
        # The quiz must carry its course directly (Quiz.course), since that is
        # how the analytics signal now resolves which course to recompute.
        quiz = Quiz.objects.create(title="Scores dynamiques", description="", difficulty="easy", course=self.course)
        question = Question.objects.create(quiz=quiz, prompt="Notion", type="single_choice", difficulty="easy")
        concept = Concept.objects.create(course=self.course, code="dynamic", title="Notion dynamique")
        QuestionConcept.objects.create(question_id=question.pk, concept=concept)
        # Performance is now computed from correct_answers/total_questions,
        # not from a raw "score" field, so these need to be set explicitly.
        for correct, total in ((6, 10), (8, 10)):
            attempt = QuizAttempt.objects.create(user=self.user, quiz=quiz)
            Evaluation.objects.create(attempt=attempt, score=correct * 10, correct_answers=correct,
                                      total_questions=total, feedback="")
        performance = Performance.objects.get(user=self.user, course=self.course)
        self.assertEqual(performance.average_score, 70)
        self.assertEqual(performance.quiz_count, 2)
        response = self.client.get(reverse("performance-list"))
        self.assertEqual(response.data["average_score"], 70)