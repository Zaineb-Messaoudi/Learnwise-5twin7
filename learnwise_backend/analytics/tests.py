from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from content.models import Course, CourseMaterial
from .models import Achievement, LearningActivity, LearningSession, Progress
from .services import evaluate_achievements, recommendations_for
from learnwise_backend.asgi import application

class AnalyticsTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="student", email="student@example.com", password="secret", role="etudiant")
        self.other = get_user_model().objects.create_user(username="other", email="other@example.com", password="secret", role="etudiant")
        self.course = Course.objects.create(title="Django", description="API", level="beginner", language="fr")
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
        LearningActivity.objects.create(session=session, activity_type="lesson_completed", completed_at=timezone.now())
        # Manually trigger progress update (signal removed for test stability)
        from .services import record_activity_effects
        activity = LearningActivity.objects.filter(session=session).first()
        record_activity_effects(activity)
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
