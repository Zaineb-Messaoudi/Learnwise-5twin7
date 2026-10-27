from django.apps import apps
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
    course_id = serializers.PrimaryKeyRelatedField(source="course", queryset=apps.get_model("content", "Course").objects.all(), write_only=True)
    course = CourseSummarySerializer(read_only=True)
    class Meta:
        model = Enrollment
        fields = ("id", "course", "course_id", "learning_path", "enrolled_at", "status")
        read_only_fields = ("id", "enrolled_at")
    def create(self, validated_data):
        course = validated_data.pop("course")
        enrollment, _ = Enrollment.objects.update_or_create(
            user=self.context["request"].user, course=course, defaults=validated_data
        )
        Progress.objects.get_or_create(user=enrollment.user, course=course)
        Performance.objects.get_or_create(user=enrollment.user, course=course)
        return enrollment

class LearningSessionSerializer(serializers.ModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(source="course", queryset=apps.get_model("content", "Course").objects.all(), write_only=True)
    course = CourseSummarySerializer(read_only=True)
    class Meta:
        model = LearningSession
        fields = ("id", "course", "course_id", "started_at", "ended_at", "duration")
        read_only_fields = ("id", "started_at", "duration")

class LearningActivitySerializer(serializers.ModelSerializer):
    session_id = serializers.PrimaryKeyRelatedField(source="session", queryset=LearningSession.objects.all(), write_only=True)
    material_id = serializers.CharField(required=False, allow_null=True, write_only=True)
    class Meta:
        model = LearningActivity
        fields = ("id", "session", "session_id", "activity_type", "reference_id", "material_id", "started_at", "completed_at")
        read_only_fields = ("id", "session", "started_at")
    def validate_session_id(self, session):
        if session.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("This session does not belong to you.")
        return session
    def create(self, validated_data):
        import uuid
        material_id = validated_data.pop("material_id", None)
        if material_id:
            try:
                validated_data["reference_id"] = uuid.UUID(str(material_id))
            except ValueError:
                validated_data["reference_id"] = uuid.uuid5(uuid.NAMESPACE_URL, f"content-material:{material_id}")
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
