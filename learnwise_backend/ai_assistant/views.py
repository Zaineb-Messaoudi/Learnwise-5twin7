from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AssistantSession, VoiceQuestion, AssistantMessage, Explanation, Illustration
from .serializers import (
    AssistantSessionSerializer, VoiceQuestionSerializer,
    AssistantMessageSerializer, ExplanationSerializer, IllustrationSerializer,
)


class AssistantSessionViewSet(viewsets.ModelViewSet):
    serializer_class = AssistantSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AssistantSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        session = self.get_object()  # already filtered by user
        if request.method == 'GET':
            messages = session.messages.all()
            return Response(AssistantMessageSerializer(messages, many=True).data)
        serializer = AssistantMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='illustrations')
    def generate_illustration(self, request, pk=None):
        session = self.get_object()
        return Response({'detail': 'Illustration generation not yet implemented.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class VoiceQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = VoiceQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session_id = self.request.query_params.get('session')
        if session_id:
            return VoiceQuestion.objects.filter(session_id=session_id, session__user=self.request.user)
        return VoiceQuestion.objects.filter(session__user=self.request.user)

    def perform_create(self, serializer):
        session_id = self.request.data.get('session')
        try:
            session = AssistantSession.objects.get(id=session_id, user=self.request.user)
        except AssistantSession.DoesNotExist:
            raise permissions.PermissionDenied("Session not found or not yours.")
        serializer.save(session=session)


class AssistantMessageViewSet(viewsets.ModelViewSet):
    serializer_class = AssistantMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session_id = self.request.query_params.get('session')
        if session_id:
            return AssistantMessage.objects.filter(session_id=session_id, session__user=self.request.user)
        return AssistantMessage.objects.filter(session__user=self.request.user)

    def perform_create(self, serializer):
        session = serializer.validated_data['session']
        if session.user_id != self.request.user.id:
            raise permissions.PermissionDenied("Session not found or not yours.")
        serializer.save()


class ExplanationViewSet(viewsets.ModelViewSet):
    serializer_class = ExplanationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Explanation.objects.filter(message__session__user=self.request.user)

    def perform_create(self, serializer):
        message = serializer.validated_data['message']
        if message.session.user_id != self.request.user.id:
            raise permissions.PermissionDenied("Message not found or not yours.")
        serializer.save()


class IllustrationViewSet(viewsets.ModelViewSet):
    serializer_class = IllustrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Illustration.objects.filter(message__session__user=self.request.user)

    def perform_create(self, serializer):
        message = serializer.validated_data['message']
        if message.session.user_id != self.request.user.id:
            raise permissions.PermissionDenied("Message not found or not yours.")
        serializer.save()
