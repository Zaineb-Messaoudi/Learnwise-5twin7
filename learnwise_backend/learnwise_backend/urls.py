"""
URL configuration for learnwise_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/content/', include('content.urls')),
    path('api/v1/ai/', include('ai_assistant.urls')),
    path('api/v1/assessment/', include('assessment.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/notebooks/', include('notebooks.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)