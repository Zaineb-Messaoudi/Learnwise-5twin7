from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("learning-paths", views.LearningPathViewSet)
router.register("enrollments", views.EnrollmentViewSet)
router.register("learning-sessions", views.LearningSessionViewSet)
router.register("learning-activities", views.LearningActivityViewSet)
router.register("progress", views.ProgressViewSet)
router.register("performance", views.PerformanceViewSet)
router.register("achievements", views.AchievementViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/", views.dashboard, name="analytics-dashboard"),
    path("student/overview/", views.dashboard, name="student-overview"),
    path("recommendations/", views.recommendations, name="recommendations"),
    path("sessions/start/", views.LearningSessionViewSet.as_view({"post": "start"}), name="session-start"),
    path("sessions/<uuid:pk>/end/", views.LearningSessionViewSet.as_view({"post": "end"}), name="session-end"),
]
