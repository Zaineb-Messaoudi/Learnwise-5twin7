from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AssistantMessage,
    AssistantSession,
    Explanation,
    Illustration,
    ProcessingStatus,
    VoiceQuestion,
)
from .serializers import (
    AssistantMessageSerializer,
    AssistantSessionSerializer,
    MessageCreateSerializer,
    VoiceQuestionCreateSerializer,
    VoiceQuestionSerializer,
)
from .services.context import build_context
from .services.errors import AIServiceError
from .services.gemini_service import (
    build_image_prompt,
    generate_answer,
    generate_explanation,
)
from .services.illustration_service import generate_image
from .services.transcription_service import transcribe_audio

IsAuthenticated = permissions.IsAuthenticated


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def ai_error_response(exc):
    return Response(
        {
            'detail': exc.message,
            'error_code': exc.code,
            'retryable': exc.retryable,
        },
        status=status.HTTP_502_BAD_GATEWAY,
    )


@api_view(['GET'])
def api_root(request):
    return Response({'sessions': request.build_absolute_uri('sessions/')})


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------
class SessionListCreateView(generics.ListCreateAPIView):
    serializer_class = AssistantSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return AssistantSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AssistantSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'session_id'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return AssistantSession.objects.filter(user=self.request.user)


# --------------------------------------------------------------------------
# Messages
# --------------------------------------------------------------------------
class SessionMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = AssistantMessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def _session(self):
        return get_object_or_404(
            AssistantSession, pk=self.kwargs['session_id'], user=self.request.user
        )

    def get_queryset(self):
        return self._session().messages.prefetch_related(
            'illustrations', 'explanations'
        )

    def create(self, request, *args, **kwargs):
        session = self._session()
        payload = MessageCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        question = data['content'].strip()
        course_id = data.get('course_id') or session.course_id

        # Historique recent (avant d'ajouter la nouvelle question).
        recent = list(
            session.messages.filter(status=ProcessingStatus.COMPLETED)
            .exclude(content='')
            .order_by('-created_at', '-id')[:10]
        )
        history = [(m.role, m.content) for m in reversed(recent)]

        AssistantMessage.objects.create(
            session=session,
            role=AssistantMessage.Role.USER,
            content=question,
            status=ProcessingStatus.COMPLETED,
        )
        if not session.title:
            session.title = question[:60]
            session.save(update_fields=['title', 'updated_at'])

        reply = AssistantMessage.objects.create(
            session=session,
            role=AssistantMessage.Role.ASSISTANT,
            status=ProcessingStatus.PROCESSING,
        )
        try:
            context, citations = build_context(course_id, data.get('material_ids'))
            reply.content = generate_answer(question, history, context)
            reply.citations = citations
            reply.status = ProcessingStatus.COMPLETED
        except AIServiceError as exc:
            reply.status = ProcessingStatus.FAILED
            reply.error_code = exc.code
            reply.error_message = exc.message
        reply.save()

        body = AssistantMessageSerializer(reply, context={'request': request}).data
        code = (
            status.HTTP_201_CREATED
            if reply.status == ProcessingStatus.COMPLETED
            else status.HTTP_502_BAD_GATEWAY
        )
        return Response(body, status=code)


class MessageDetailView(generics.RetrieveAPIView):
    serializer_class = AssistantMessageSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'message_id'

    def get_queryset(self):
        return AssistantMessage.objects.filter(
            session__user=self.request.user
        ).prefetch_related('illustrations', 'explanations')


# --------------------------------------------------------------------------
# Questions vocales
# --------------------------------------------------------------------------
class VoiceQuestionCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, session_id):
        session = get_object_or_404(
            AssistantSession, pk=session_id, user=request.user
        )
        payload = VoiceQuestionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        question = VoiceQuestion.objects.create(
            session=session,
            audio_file=payload.validated_data['audio'],
            language=payload.validated_data.get('language', ''),
            status=ProcessingStatus.PROCESSING,
            progress=10,
        )
        try:
            question.transcription = transcribe_audio(question.audio_file.path)
            question.status = ProcessingStatus.COMPLETED
            question.progress = 100
        except AIServiceError as exc:
            question.status = ProcessingStatus.FAILED
            question.error_code = exc.code
            question.error_message = exc.message
        question.save()

        body = VoiceQuestionSerializer(question, context={'request': request}).data
        return Response(body, status=status.HTTP_201_CREATED)


class VoiceQuestionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VoiceQuestionSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'question_id'
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        return VoiceQuestion.objects.filter(session__user=self.request.user)


# --------------------------------------------------------------------------
# Explication et illustration (declenchees a la demande)
# --------------------------------------------------------------------------
def _assistant_message_or_404(request, message_id):
    return get_object_or_404(
        AssistantMessage,
        pk=message_id,
        session__user=request.user,
        role=AssistantMessage.Role.ASSISTANT,
        status=ProcessingStatus.COMPLETED,
    )


class MessageExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = _assistant_message_or_404(request, message_id)
        level = request.data.get(
            'difficulty_level', Explanation.Difficulty.INTERMEDIATE
        )
        if level not in Explanation.Difficulty.values:
            return Response(
                {
                    'detail': 'Correct the highlighted fields.',
                    'errors': {'difficulty_level': ['Invalid choice.']},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            text = generate_explanation(message.content, level)
        except AIServiceError as exc:
            return ai_error_response(exc)

        Explanation.objects.create(
            message=message, content=text, difficulty_level=level
        )
        body = AssistantMessageSerializer(message, context={'request': request}).data
        return Response(body, status=status.HTTP_201_CREATED)


class MessageIllustrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = _assistant_message_or_404(request, message_id)
        illustration = Illustration.objects.create(
            message=message, prompt='', status=ProcessingStatus.PROCESSING
        )
        try:
            prompt = build_image_prompt(message.content)
            illustration.prompt = prompt
            png = generate_image(prompt)
            illustration.image.save(
                f'{illustration.pk}.png', ContentFile(png), save=False
            )
            illustration.status = ProcessingStatus.COMPLETED
        except AIServiceError as exc:
            illustration.status = ProcessingStatus.FAILED
            illustration.error_message = exc.message
        illustration.save()

        body = AssistantMessageSerializer(message, context={'request': request}).data
        code = (
            status.HTTP_201_CREATED
            if illustration.status == ProcessingStatus.COMPLETED
            else status.HTTP_502_BAD_GATEWAY
        )
        return Response(body, status=code)
