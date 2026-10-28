"""
URL configuration for learnwise_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """Simple health check endpoint for load balancers and monitoring."""
    db_status = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_status = "error"

    return JsonResponse({
        "status": "ok",
        "database": db_status,
    })


# Import both url pattern sets from accounts
from accounts.urls import auth_urlpatterns as accounts_auth_urls
from accounts.urls import urlpatterns as accounts_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('api/v1/auth/', include((accounts_auth_urls, 'auth'), namespace='auth')),
    path('api/v1/accounts/', include((accounts_urls, 'accounts'), namespace='accounts')),
    path('api/v1/content/', include('content.urls')),
    path('api/v1/ai/', include('ai_assistant.urls')),
    path('api/v1/assistant/', include('ai_assistant.urls')),
    path('api/v1/assessment/', include('assessment.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/notebooks/', include('notebooks.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)