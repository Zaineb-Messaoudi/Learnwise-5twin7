from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotebookViewSet, NotebookEntryViewSet

router = DefaultRouter()
router.register(r'entries', NotebookEntryViewSet, basename='notebook-entry')
router.register(r'', NotebookViewSet, basename='notebook')

urlpatterns = [
    path('', include(router.urls)),
]