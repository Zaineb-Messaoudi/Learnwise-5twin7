from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db.models import Count, Avg
from django.contrib.auth import get_user_model

from .models import LearningPath, Enrollment, LearningSession, LearningActivity, Progress, Performance, Achievement
from .serializers import (
    LearningPathSerializer, EnrollmentSerializer, LearningSessionSerializer,
    LearningActivitySerializer, ProgressSerializer, PerformanceSerializer, AchievementSerializer,
)
from content.models import Course


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Users can only modify their own records, but can read published course data."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.is_superuser or user.role == 'admin':
            return True
        return getattr(obj, 'user', None) == user


class LearningPathViewSet(viewsets.ModelViewSet):
    serializer_class = LearningPathSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LearningPath.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def enroll(self, request):
        course_id = request.data.get('course_id')
        if not course_id:
            return Response({'detail': 'course_id required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'detail': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)
        enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class LearningSessionViewSet(viewsets.ModelViewSet):
    serializer_class = LearningSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LearningSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def start(self, request):
        course_id = request.data.get('course_id')
        if not course_id:
            return Response({'detail': 'course_id required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'detail': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)
        session = LearningSession.objects.create(user=request.user, course_id=course_id, duration=0)
        return Response(LearningSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def finish(self, request, pk=None):
        session = self.get_object()
        session.ended_at = timezone.now()
        session.duration = int((session.ended_at - session.started_at).total_seconds())
        session.save()
        return Response(LearningSessionSerializer(session).data)


class LearningActivityViewSet(viewsets.ModelViewSet):
    serializer_class = LearningActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session_id = self.request.query_params.get('session')
        if session_id:
            return LearningActivity.objects.filter(session_id=session_id, session__user=self.request.user)
        return LearningActivity.objects.filter(session__user=self.request.user)

    def perform_create(self, serializer):
        session_id = self.request.data.get('session')
        try:
            session = LearningSession.objects.get(id=session_id, user=self.request.user)
        except LearningSession.DoesNotExist:
            raise permissions.PermissionDenied("Session not found or not yours.")
        serializer.save(session=session)

    @action(detail=False, methods=['post'])
    def record(self, request):
        session_id = request.data.get('session')
        if not session_id:
            return Response({'detail': 'session is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = LearningSession.objects.get(id=session_id, user=request.user)
        except LearningSession.DoesNotExist:
            return Response({'detail': 'Session not found or not yours.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProgressViewSet(viewsets.ModelViewSet):
    serializer_class = ProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        course_id = self.request.query_params.get('course')
        if course_id:
            return Progress.objects.filter(user=self.request.user, course_id=course_id)
        return Progress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PerformanceViewSet(viewsets.ModelViewSet):
    serializer_class = PerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Performance.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Only allow creating performance records for the authenticated user
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Users can only update their own performance records
        perf = self.get_object()
        if perf.user != self.request.user and not self.request.user.is_superuser:
            raise permissions.PermissionDenied("Non autorisé.")
        serializer.save()


class AchievementViewSet(viewsets.ModelViewSet):
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Achievement.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
def student_overview(request):
    try:
        range_days = int(request.query_params.get('range', '30'))
    except (ValueError, TypeError):
        return Response({'detail': 'Invalid range parameter.'}, status=status.HTTP_400_BAD_REQUEST)
    since = timezone.now() - timedelta(days=range_days)
    user = request.user
    enrollments = Enrollment.objects.filter(user=user)
    sessions = LearningSession.objects.filter(user=user, started_at__gte=since)
    return Response({
        'enrollments_count': enrollments.count(),
        'sessions_count': sessions.count(),
        'total_duration': sum(s.duration or 0 for s in sessions),
        'completed_courses': enrollments.filter(status='completed').count(),
    })


@api_view(['GET'])
def teacher_overview(request):
    try:
        range_days = int(request.query_params.get('range', '30'))
    except (ValueError, TypeError):
        return Response({'detail': 'Invalid range parameter.'}, status=status.HTTP_400_BAD_REQUEST)
    since = timezone.now() - timedelta(days=range_days)
    user = request.user
    if not (user.is_superuser or user.role in ('professeur', 'teacher', 'admin')):
        return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
    courses_taught = Course.objects.filter(owner=user)
    return Response({
        'courses_count': courses_taught.count(),
        'published_courses': courses_taught.filter(status='published').count(),
        'total_students': Enrollment.objects.filter(course__in=courses_taught).count(),
    })


@api_view(['GET'])
def admin_overview(request):
    if not (request.user.is_superuser or request.user.role == 'admin'):
        return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        range_days = int(request.query_params.get('range', '30'))
    except (ValueError, TypeError):
        return Response({'detail': 'Invalid range parameter.'}, status=status.HTTP_400_BAD_REQUEST)
    User = get_user_model()
    since = timezone.now() - timedelta(days=range_days)
    return Response({
        'total_users': User.objects.count(),
        'total_courses': Course.objects.count(),
        'total_enrollments': Enrollment.objects.filter(enrolled_at__gte=since).count(),
    })
