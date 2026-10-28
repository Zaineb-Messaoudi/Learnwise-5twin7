from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("learning-paths", views.LearningPathViewSet, basename="learning-path")
router.register("enrollments", views.EnrollmentViewSet, basename="enrollment")
router.register("learning-sessions", views.LearningSessionViewSet, basename="learning-session")
router.register("learning-activities", views.LearningActivityViewSet, basename="learning-activity")
router.register("progress", views.ProgressViewSet, basename="progress")
router.register("performance", views.PerformanceViewSet, basename="performance")
router.register("achievements", views.AchievementViewSet, basename="achievement")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/", views.dashboard, name="analytics-dashboard"),
    path("student/overview/", views.dashboard, name="student-overview"),
    path("teacher/overview/", views.teacher_overview, name="teacher-overview"),
    path("admin/overview/", views.admin_overview, name="admin-overview"),
    path("recommendations/", views.recommendations, name="recommendations"),
    path("sessions/start/", views.LearningSessionViewSet.as_view({"post": "start"}), name="session-start"),
    path("sessions/<uuid:pk>/end/", views.LearningSessionViewSet.as_view({"post": "end"}), name="session-end"),
]