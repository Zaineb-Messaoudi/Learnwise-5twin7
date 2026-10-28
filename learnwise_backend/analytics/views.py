from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsStudent
from content.models import Course
from .models import Achievement, Enrollment, LearningActivity, LearningPath, LearningSession, Performance, Progress
from .permissions import AnalyticsRolePermission
from .serializers import (AchievementSerializer, EnrollmentSerializer, LearningActivitySerializer, LearningPathSerializer,
                          LearningSessionSerializer, PerformanceSerializer, ProgressSerializer)
from .services import dashboard_for, evaluate_achievements, recommendations_for


class OwnedQuerysetMixin:
    permission_classes = (permissions.IsAuthenticated, AnalyticsRolePermission)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == "etudiant":
            return queryset.filter(user=user)
        if user.role == "professeur":
            if queryset.model.__name__ == "LearningActivity":
                return queryset.filter(session__course__owner=user)
            return queryset.filter(course__owner=user) if hasattr(queryset.model, "course") else queryset.none()
        if user.role not in ("admin", "teacher") and not user.is_superuser:
            return queryset.none()
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LearningPathViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset, serializer_class = LearningPath.objects.all(), LearningPathSerializer


class EnrollmentViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related("course", "learning_path")
    serializer_class = EnrollmentSerializer
    http_method_names = ("get", "post", "patch", "head", "options")


class LearningSessionViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LearningSession.objects.select_related("course")
    serializer_class = LearningSessionSerializer
    http_method_names = ("get", "post", "patch", "head", "options")

    def perform_update(self, serializer):
        ended_at = serializer.validated_data.get("ended_at")
        if ended_at and not serializer.instance.ended_at:
            serializer.instance.end(ended_at)
            evaluate_achievements(serializer.instance.user)
        else:
            serializer.save()

    @action(detail=False, methods=("post",), url_path="start")
    def start(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("post",), url_path="end")
    def end(self, request, pk=None):
        session = self.get_object()
        if not session.ended_at:
            session.end()
            evaluate_achievements(request.user)
        return Response(self.get_serializer(session).data)


class LearningActivityViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LearningActivity.objects.select_related("session", "session__course")
    serializer_class = LearningActivitySerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.role == "etudiant":
            queryset = queryset.filter(session__user=self.request.user)
        return queryset.filter(session_id=self.request.query_params["session"]) if self.request.query_params.get("session") else queryset

    def perform_create(self, serializer):
        serializer.save()


class ProgressViewSet(OwnedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset, serializer_class = Progress.objects.select_related("course"), ProgressSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(course_id=self.request.query_params["course"]) if self.request.query_params.get("course") else queryset

    def retrieve(self, request, pk=None):
        if request.user.role == "etudiant":
            obj = self.get_queryset().filter(course_id=pk).first()
            if obj is None:
                obj = self.get_object()
        else:
            obj = self.get_object()
        return Response(self.get_serializer(obj).data)


class PerformanceViewSet(OwnedQuerysetMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset, serializer_class = Performance.objects.select_related("course"), PerformanceSerializer

    def list(self, request):
        queryset = self.get_queryset()
        average = queryset.aggregate(value=Avg("average_score"))["value"] or 0
        topics = [{"name": item.course.title, "score": round(item.average_score),
                   "trend": "Strong topic" if item.average_score >= 80 else "Worth another review"} for item in queryset]
        return Response({"data_source": "live", "average_score": round(average, 1),
                         "strong_topics": sum(item["score"] >= 80 for item in topics), "topics": topics,
                         "results": self.get_serializer(queryset, many=True).data})


class AchievementViewSet(OwnedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset, serializer_class = Achievement.objects.all(), AchievementSerializer


def _range_days(request):
    try:
        return min(max(int(request.query_params.get("range", "30d").rstrip("d")), 1), 365)
    except (ValueError, TypeError, OverflowError):
        return 30


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated, IsStudent))
def dashboard(request):
    return Response(dashboard_for(request.user, _range_days(request)))


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated, IsStudent))
def recommendations(request):
    return Response(recommendations_for(request.user))


@api_view(["GET"])
def teacher_overview(request):
    try:
        range_days = _range_days(request)
    except (ValueError, TypeError, OverflowError):
        return Response({"detail": "Invalid range parameter."}, status=status.HTTP_400_BAD_REQUEST)
    since = timezone.now() - timedelta(days=range_days)
    user = request.user
    if not (user.is_superuser or user.role in ("professeur", "teacher", "admin")):
        return Response({"detail": "Non autorisé."}, status=status.HTTP_403_FORBIDDEN)
    courses_taught = Course.objects.filter(owner=user)
    return Response({
        "courses_count": courses_taught.count(),
        "published_courses": courses_taught.filter(status="published").count(),
        "total_students": Enrollment.objects.filter(course__in=courses_taught).count(),
    })


@api_view(["GET"])
def admin_overview(request):
    if not (request.user.is_superuser or request.user.role == "admin"):
        return Response({"detail": "Non autorisé."}, status=status.HTTP_403_FORBIDDEN)
    try:
        range_days = _range_days(request)
    except (ValueError, TypeError, OverflowError):
        return Response({"detail": "Invalid range parameter."}, status=status.HTTP_400_BAD_REQUEST)
    User = get_user_model()
    since = timezone.now() - timedelta(days=range_days)
    return Response({
        "total_users": User.objects.count(),
        "total_courses": Course.objects.count(),
        "total_enrollments": Enrollment.objects.filter(enrolled_at__gte=since).count(),
    })
