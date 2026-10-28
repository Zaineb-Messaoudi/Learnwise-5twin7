import os

from rest_framework import serializers

from content.models import Course

from .models import (
    AssistantMessage,
    AssistantSession,
    Explanation,
    Illustration,
    VoiceQuestion,
)

ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.webm', '.ogg', '.m4a'}
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MiB


class StringIdSerializer(serializers.ModelSerializer):
    """Le contrat demande des identifiants opaques de type string."""

    string_id_fields = ('id', 'session')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for name in self.string_id_fields:
            if data.get(name) is not None:
                data[name] = str(data[name])
        return data


class AssistantSessionSerializer(StringIdSerializer):
    string_id_fields = ('id', 'course_id')
    course_id = serializers.PrimaryKeyRelatedField(
        source='course',
        queryset=Course.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = AssistantSession
        fields = [
            'id', 'title', 'course_id', 'status',
            'started_at', 'ended_at', 'updated_at',
        ]
        read_only_fields = ['started_at', 'ended_at', 'updated_at']


class IllustrationSerializer(StringIdSerializer):
    string_id_fields = ('id',)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Illustration
        fields = ['id', 'prompt', 'image', 'status', 'error_message', 'created_at']


class ExplanationSerializer(StringIdSerializer):
    string_id_fields = ('id',)

    class Meta:
        model = Explanation
        fields = ['id', 'content', 'difficulty_level', 'created_at']


class AssistantMessageSerializer(StringIdSerializer):
    explanation = serializers.SerializerMethodField()
    illustrations = IllustrationSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantMessage
        fields = [
            'id', 'session', 'role', 'content', 'status', 'created_at',
            'explanation', 'illustrations', 'citations',
            'error_code', 'error_message',
        ]

    def get_explanation(self, obj):
        latest = obj.explanations.order_by('-id').first()
        if latest is None:
            return None
        return ExplanationSerializer(latest, context=self.context).data


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=8000)
    course_id = serializers.IntegerField(required=False, allow_null=True)
    material_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )


class VoiceQuestionSerializer(StringIdSerializer):
    transcript = serializers.CharField(
        source='transcription', required=False, allow_blank=True
    )
    audio_file = serializers.FileField(read_only=True)

    class Meta:
        model = VoiceQuestion
        fields = [
            'id', 'session', 'audio_file', 'language', 'transcript',
            'status', 'progress', 'error_code', 'error_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'session', 'language', 'status', 'progress',
            'error_code', 'error_message', 'created_at', 'updated_at',
        ]


class VoiceQuestionCreateSerializer(serializers.Serializer):
    audio = serializers.FileField()
    language = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def validate_audio(self, value):
        extension = os.path.splitext(value.name)[1].lower()
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise serializers.ValidationError(
                "Format non supporte. Formats acceptes : "
                + ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
            )
        if value.size > MAX_AUDIO_BYTES:
            raise serializers.ValidationError(
                "Fichier trop volumineux (maximum 25 Mo)."
            )
        return value
