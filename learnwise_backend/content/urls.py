from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'chapters', views.ChapterViewSet, basename='chapter')
router.register(r'materials', views.CourseMaterialViewSet, basename='coursematerial')
router.register(r'audio', views.AudioMaterialViewSet, basename='audiomaterial')
router.register(r'documents', views.DocumentMaterialViewSet, basename='documentmaterial')
router.register(r'videos', views.VideoMaterialViewSet, basename='videomaterial')
router.register(r'transcriptions', views.TranscriptionViewSet, basename='transcription')
router.register(r'summaries', views.SummaryViewSet, basename='summary')

urlpatterns = [
    path('', include(router.urls)),
]
