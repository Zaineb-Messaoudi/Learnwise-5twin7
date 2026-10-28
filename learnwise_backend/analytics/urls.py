from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='analytics-root'),
    path('student/overview/', views.student_overview, name='student-overview'),
]