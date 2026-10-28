from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'learning-paths', views.LearningPathViewSet, basename='learning-path')
router.register(r'enrollments', views.EnrollmentViewSet, basename='enrollment')
router.register(r'learning-sessions', views.LearningSessionViewSet, basename='learning-session')
router.register(r'learning-activities', views.LearningActivityViewSet, basename='learning-activity')
router.register(r'progress', views.ProgressViewSet, basename='progress')
router.register(r'performance', views.PerformanceViewSet, basename='performance')
router.register(r'achievements', views.AchievementViewSet, basename='achievement')

urlpatterns = [
    path('', include(router.urls)),
    path('student/overview/', views.student_overview, name='student-overview'),
    path('teacher/overview/', views.teacher_overview, name='teacher-overview'),
    path('admin/overview/', views.admin_overview, name='admin-overview'),
]
