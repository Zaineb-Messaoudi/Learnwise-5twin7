from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from accounts.permissions import IsProfessorOrAdmin, IsStudent
from .models import (Achievement, Cohort, Enrollment, Intervention, LearningActivity, LearningPath,
                     LearningSession, Performance, Progress)
from content.models import Course
from .permissions import AnalyticsRolePermission
from .serializers import (AchievementSerializer, EnrollmentSerializer, LearningActivitySerializer, LearningPathSerializer,
                          LearningSessionSerializer, PerformanceSerializer, ProgressSerializer)
from .services import dashboard_for, evaluate_achievements, recommendations_for
from .reporting import cohort_comparison, concept_weaknesses, student_course_indicators
from .radar import evaluate_course_risk, radar_for


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
        measured = list(queryset.filter(quiz_count__gt=0))
        attempts = sum(item.quiz_count for item in measured)
        average = sum(item.average_score * item.quiz_count for item in measured) / attempts if attempts else 0
        topics = [{"name": item.course.title, "score": round(item.average_score),
                   "trend": "Strong topic" if item.average_score >= 80 else "Worth another review",
                   "attempts": item.quiz_count} for item in measured]
        return Response({"data_source": "live", "average_score": round(average, 1),
                         "assessment_count": attempts,
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

@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated, IsStudent))
def student_indicators(request):
    return Response(student_course_indicators(request.user))

@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated, IsStudent))
def weaknesses(request):
    try:
        minimum = min(max(int(request.query_params.get("minimum_answers", 2)), 1), 100)
    except ValueError:
        minimum = 2
    return Response(concept_weaknesses(request.user, minimum))

@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated, IsProfessorOrAdmin))
def cohort_report(request, cohort_id):
    from django.shortcuts import get_object_or_404
    return Response(cohort_comparison(get_object_or_404(Cohort, pk=cohort_id)))

@api_view(("GET", "POST"))
@permission_classes((permissions.IsAuthenticated, IsStudent))
def learning_radar(request):
    if request.method == "POST":
        courses = request.user.enrollments.exclude(status=Enrollment.Status.DROPPED).select_related("course")
        for enrollment in courses:
            # Compatibility for older frontend bundles: their query used POST
            # and invalidated itself after every WebSocket notification. Keep
            # evaluation available without producing a feedback loop.
            evaluate_course_risk(request.user, enrollment.course, notify=False)
    return Response(radar_for(request.user))

@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated, IsStudent))
def complete_intervention(request, intervention_id):
    from django.shortcuts import get_object_or_404
    intervention = get_object_or_404(Intervention, pk=intervention_id, risk__user=request.user)
    if not intervention.completed_at:
        intervention.completed_at = timezone.now()
        intervention.save(update_fields=("completed_at",))
    return Response({"id": str(intervention.pk), "completed_at": intervention.completed_at})

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



@api_view(['GET'])
def student_overview(request):
    range_days = int(request.query_params.get('range', 30))
    return Response({
        'range_days': range_days,
        'total_hours': 12.4,
        'average_score': 87,
        'sessions': 8,
        'topics': [
            {'name': 'Neural Networks', 'score': 82, 'trend': 'up'},
            {'name': 'Gradient Descent', 'score': 76, 'trend': 'stable'},
            {'name': 'Backpropagation', 'score': 91, 'trend': 'up'},
        ],
        'weekly_activity': [
            {'day': 'Mon', 'hours': 1.2, 'score': 76},
            {'day': 'Tue', 'hours': 2.4, 'score': 82},
            {'day': 'Wed', 'hours': 1.8, 'score': 88},
            {'day': 'Thu', 'hours': 3.1, 'score': 91},
            {'day': 'Fri', 'hours': 2.2, 'score': 87},
            {'day': 'Sat', 'hours': 1.4, 'score': 94},
            {'day': 'Sun', 'hours': 2.8, 'score': 90},
        ],
    })
