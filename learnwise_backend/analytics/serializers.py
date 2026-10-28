from django.apps import apps
from django.utils import timezone
from rest_framework import serializers
from .models import Achievement, Enrollment, LearningActivity, LearningPath, LearningSession, Performance, Progress


class CourseSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()


class LearningPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPath
        fields = ("id", "title", "description", "created_at")
        read_only_fields = ("id", "created_at")


class EnrollmentSerializer(serializers.ModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(source="course", queryset=apps.get_model("content", "Course").objects.filter(status="published"), write_only=True)
    course = CourseSummarySerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ("id", "course", "course_id", "learning_path", "enrolled_at", "status")
        read_only_fields = ("id", "enrolled_at")

    def create(self, validated_data):
        if self.context["request"].user.role != "etudiant":
            raise serializers.ValidationError("Only students can enroll.")
        course = validated_data.pop("course")
        enrollment, _ = Enrollment.objects.update_or_create(
            user=self.context["request"].user, course=course, defaults=validated_data
        )
        from .services import ensure_enrollment
        ensure_enrollment(enrollment.user, course)
        return enrollment


class LearningSessionSerializer(serializers.ModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(source="course", queryset=apps.get_model("content", "Course").objects.all(), write_only=True)
    course = CourseSummarySerializer(read_only=True)

    class Meta:
        model = LearningSession
        fields = ("id", "course", "course_id", "started_at", "ended_at", "duration")
        read_only_fields = ("id", "started_at", "duration")

    def validate(self, attrs):
        if self.instance is None and attrs.get("ended_at") is not None:
            raise serializers.ValidationError({"ended_at": "A session must be ended through the end endpoint."})
        started = attrs.get("started_at", self.instance.started_at if self.instance else timezone.now())
        ended = attrs.get("ended_at")
        if ended is not None and (ended < started or ended > timezone.now()):
            raise serializers.ValidationError({"ended_at": "ended_at must be between started_at and now."})
        return attrs


class LearningActivitySerializer(serializers.ModelSerializer):
    session_id = serializers.PrimaryKeyRelatedField(source="session", queryset=LearningSession.objects.all(), write_only=True)
    material_id = serializers.PrimaryKeyRelatedField(source="material", required=False, allow_null=True, write_only=True, queryset=apps.get_model("content", "CourseMaterial").objects.all())

    class Meta:
        model = LearningActivity
        fields = ("id", "session", "session_id", "activity_type", "material_id", "started_at", "completed_at")
        read_only_fields = ("id", "session", "started_at")

    def validate_session_id(self, session):
        if session.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("This session does not belong to you.")
        return session

    def validate(self, attrs):
        material = attrs.get("material")
        session = attrs.get("session")
        if material and session and material.course_id != session.course_id:
            raise serializers.ValidationError({"material_id": "This material is not part of the session course."})
        return attrs

    def create(self, validated_data):
        return super().create(validated_data)


class ProgressSerializer(serializers.ModelSerializer):
    course = CourseSummarySerializer(read_only=True)

    class Meta:
        model = Progress
        fields = ("id", "course", "completion_percentage", "last_activity")


class PerformanceSerializer(serializers.ModelSerializer):
    course = CourseSummarySerializer(read_only=True)

    class Meta:
        model = Performance
        fields = ("id", "course", "average_score", "quiz_count", "exercise_count", "updated_at")


class AchievementSerializer(serializers.ModelSerializer):
    detail = serializers.CharField(source="description", read_only=True)
    status = serializers.SerializerMethodField()
    progress = serializers.IntegerField(default=100, read_only=True)

    class Meta:
        model = Achievement
        fields = ("id", "code", "title", "description", "detail", "earned_at", "status", "progress")

    def get_status(self, obj):
        return "earned"
