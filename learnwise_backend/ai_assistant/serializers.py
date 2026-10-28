from rest_framework import serializers
from .models import AssistantSession, VoiceQuestion, AssistantMessage, Explanation, Illustration


class AssistantSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantSession
        fields = '__all__'


class VoiceQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceQuestion
        fields = '__all__'


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = '__all__'


class ExplanationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Explanation
        fields = '__all__'


class IllustrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Illustration
        fields = '__all__'
