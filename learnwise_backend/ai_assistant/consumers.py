import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone as django_timezone
from rest_framework_simplejwt.exceptions import InvalidToken

from .models import (
    AssistantMessage,
    AssistantSession,
    Explanation,
    Illustration,
    ProcessingStatus,
    VoiceQuestion,
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

logger = logging.getLogger(__name__)


class AssistantConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket pour l'assistant virtuel en temps real.

    Route : /ws/assistant/sessions/{session_id}/
    Enveloppe JSON : { type, id, created_at, payload }
    """

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f'assistant_session_{self.session_id}'

        user = await self._authenticate()
        if user is None:
            await self.close(code=4001)
            return

        self.user = user

        session_ok = await self._check_session()
        if not session_ok:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')
        msg_id = content.get('id')

        try:
            if msg_type == 'message.send':
                await self._handle_message_send(content, msg_id)
            elif msg_type == 'voice.transcribe':
                await self._handle_voice_transcribe(content, msg_id)
            elif msg_type == 'illustration.generate':
                await self._handle_illustration_generate(content, msg_id)
            elif msg_type == 'explanation.generate':
                await self._handle_explanation_generate(content, msg_id)
            else:
                await self._send_error(msg_id or 'unknown', 'unknown_type', "Type de message non supporte.")
        except AIServiceError as exc:
            await self._send_error(msg_id or 'unknown', exc.code, exc.message, retryable=exc.retryable)
        except Exception:
            logger.exception("Erreur WebSocket inattendue")
            await self._send_error(msg_id or 'unknown', 'internal_error', "Erreur interne du serveur.", retryable=True)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _handle_message_send(self, content, msg_id):
        payload = content.get('payload', {})
        question = (payload.get('content') or '').strip()
        course_id = payload.get('course_id')
        material_ids = payload.get('material_ids', [])

        if not question:
            await self._send_error(msg_id, 'empty_content', "Le contenu du message est vide.")
            return

        session = await self._get_session()

        # Message utilisateur
        await self._create_user_message(session, question)

        # Mettre a jour le titre si besoin
        await self._update_session_title(session, question)

        # Reponse assistant en statut processing
        assistant_msg = await self._create_assistant_message(session)

        # Construire le contexte et generer la reponse
        context, citations = await self._build_context(course_id, material_ids)
        history = await self._get_recent_history(session)

        try:
            answer_text = await self._generate_answer(question, history, context)
            await self._complete_message(assistant_msg, answer_text, citations)

            # Diffuser l'evenement complet
            data = await self._serialize_message(assistant_msg)
            await self._send_json({
                'type': 'message.completed',
                'id': msg_id,
                'created_at': self._now_iso(),
                'payload': {'message': data},
            })
        except AIServiceError as exc:
            await self._fail_message(assistant_msg, exc)
            await self._send_error(msg_id, exc.code, exc.message, retryable=exc.retryable)

    async def _handle_voice_transcribe(self, content, msg_id):
        # Le client envoie les octets audio en base64 ou l'id d'une VoiceQuestion deja creee
        payload = content.get('payload', {})
        audio_b64 = payload.get('audio')
        language = payload.get('language', '')

        if not audio_b64:
            await self._send_error(msg_id, 'missing_audio', "Aucun audio fourni.")
            return

        import base64
        import tempfile
        import os

        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            await self._send_error(msg_id, 'invalid_audio', "Audio encodage base64 invalide.")
            return

        # Ecrire dans un fichier temporaire pour le transmettre au service de transcription
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            session = await self._get_session()
            question = await self._create_voice_question(session, tmp_path, language)

            # Transcrire
            transcription = await self._transcribe(tmp_path)
            question.transcription = transcription
            question.status = ProcessingStatus.COMPLETED
            question.progress = 100
            await database_sync_to_async(question.save)(
                update_fields=['transcription', 'status', 'progress', 'updated_at']
            )

            await self._send_json({
                'type': 'voice.transcription.completed',
                'id': msg_id,
                'created_at': self._now_iso(),
                'payload': {
                    'question_id': str(question.id),
                    'transcription': transcription,
                    'status': question.status,
                },
            })
        except AIServiceError as exc:
            await self._send_error(msg_id, exc.code, exc.message, retryable=exc.retryable)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def _handle_illustration_generate(self, content, msg_id):
        payload = content.get('payload', {})
        message_id = payload.get('message_id')
        prompt = (payload.get('prompt') or '').strip()

        message = await self._get_assistant_message(message_id)
        if message is None:
            await self._send_error(msg_id, 'message_not_found', "Message assistant introuvable.")
            return

        illustration = await self._create_illustration(message, prompt, ProcessingStatus.PROCESSING)

        try:
            if not prompt:
                prompt = await self._build_image_prompt(message.content)
                illustration.prompt = prompt
                await database_sync_to_async(illustration.save)(update_fields=['prompt'])

            png_bytes = await self._generate_image(prompt)
            await self._save_illustration_image(illustration, png_bytes)
            illustration.status = ProcessingStatus.COMPLETED
            await database_sync_to_async(illustration.save)(update_fields=['status', 'image', 'updated_at'])

            await self._send_json({
                'type': 'illustration.completed',
                'id': msg_id,
                'created_at': self._now_iso(),
                'payload': {
                    'illustration_id': str(illustration.id),
                    'prompt': illustration.prompt,
                    'image_url': illustration.image.url if illustration.image else '',
                    'status': illustration.status,
                },
            })
        except AIServiceError as exc:
            illustration.status = ProcessingStatus.FAILED
            illustration.error_message = exc.message
            await database_sync_to_async(illustration.save)(update_fields=['status', 'error_message', 'updated_at'])
            await self._send_error(msg_id, exc.code, exc.message, retryable=exc.retryable)

    async def _handle_explanation_generate(self, content, msg_id):
        payload = content.get('payload', {})
        message_id = payload.get('message_id')
        difficulty = payload.get('difficulty_level', 'intermediate')

        message = await self._get_assistant_message(message_id)
        if message is None:
            await self._send_error(msg_id, 'message_not_found', "Message assistant introuvable.")
            return

        try:
            text = await self._generate_explanation(message.content, difficulty)
            await self._create_explanation(message, text, difficulty)

            await self._send_json({
                'type': 'message.completed',
                'id': msg_id,
                'created_at': self._now_iso(),
                'payload': {
                    'explanation': {
                        'content': text,
                        'difficulty_level': difficulty,
                    }
                },
            })
        except AIServiceError as exc:
            await self._send_error(msg_id, exc.code, exc.message, retryable=exc.retryable)

    # ------------------------------------------------------------------
    # Helpers (sync-to-async wrappers)
    # ------------------------------------------------------------------

    async def _authenticate(self):
        """Recupere l'utilisateur via le token JWT dans les query params ou headers."""
        from rest_framework_simplejwt.authentication import JWTAuthentication

        token = None
        query_string = self.scope.get('query_string', b'').decode()
        for part in query_string.split('&'):
            if part.startswith('token='):
                token = part.split('=', 1)[1]
                break

        if not token:
            headers = dict(self.scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]

        if not token:
            return None

        try:
            validated = JWTAuthentication().get_validated_token(token)
            user = await database_sync_to_async(JWTAuthentication().get_user)(validated)
            return user
        except (InvalidToken, Exception):
            return None

    @database_sync_to_async
    def _check_session(self):
        try:
            session = AssistantSession.objects.get(pk=self.session_id)
            return session.user_id == self.user.id
        except AssistantSession.DoesNotExist:
            return False

    @database_sync_to_async
    def _get_session(self):
        return AssistantSession.objects.get(pk=self.session_id)

    @database_sync_to_async
    def _create_user_message(self, session, content):
        return AssistantMessage.objects.create(
            session=session,
            role=AssistantMessage.Role.USER,
            content=content,
            status=ProcessingStatus.COMPLETED,
        )

    @database_sync_to_async
    def _update_session_title(self, session, question):
        if not session.title:
            session.title = question[:60]
            session.save(update_fields=['title', 'updated_at'])

    @database_sync_to_async
    def _create_assistant_message(self, session):
        return AssistantMessage.objects.create(
            session=session,
            role=AssistantMessage.Role.ASSISTANT,
            status=ProcessingStatus.PROCESSING,
        )

    @database_sync_to_async
    def _build_context(self, course_id, material_ids):
        return build_context(course_id, material_ids)

    @database_sync_to_async
    def _get_recent_history(self, session):
        recent = list(
            session.messages.filter(status=ProcessingStatus.COMPLETED)
            .exclude(content='')
            .order_by('-created_at', '-id')[:10]
        )
        return [(m.role, m.content) for m in reversed(recent)]

    @database_sync_to_async
    def _generate_answer(self, question, history, context):
        return generate_answer(question, history, context)

    @database_sync_to_async
    def _complete_message(self, message, content, citations):
        message.content = content
        message.citations = citations
        message.status = ProcessingStatus.COMPLETED
        message.save()

    @database_sync_to_async
    def _fail_message(self, message, exc):
        message.status = ProcessingStatus.FAILED
        message.error_code = exc.code
        message.error_message = exc.message
        message.save()

    @database_sync_to_async
    def _serialize_message(self, message):
        # On ne peut pas passer le request serializer context facilement en async,
        # on reconstruit manuellement la representation necessaire.
        return {
            'id': str(message.id),
            'session': str(message.session_id),
            'role': message.role,
            'content': message.content,
            'status': message.status,
            'created_at': message.created_at.isoformat(),
            'explanation': None,
            'illustrations': [],
            'citations': message.citations or [],
            'error_code': message.error_code or '',
            'error_message': message.error_message or '',
        }

    @database_sync_to_async
    def _create_voice_question(self, session, file_path, language):
        from django.core.files.base import File
        with open(file_path, 'rb') as f:
            dj_file = File(f)
            dj_file.name = 'voice.webm'
            return VoiceQuestion.objects.create(
                session=session,
                audio_file=dj_file,
                language=language,
                status=ProcessingStatus.PROCESSING,
                progress=10,
            )

    @database_sync_to_async
    def _transcribe(self, file_path):
        return transcribe_audio(file_path)

    @database_sync_to_async
    def _get_assistant_message(self, message_id):
        try:
            return AssistantMessage.objects.get(
                pk=message_id,
                role=AssistantMessage.Role.ASSISTANT,
                status=ProcessingStatus.COMPLETED,
                session__user_id=self.user.id,
            )
        except AssistantMessage.DoesNotExist:
            return None

    @database_sync_to_async
    def _create_illustration(self, message, prompt, status):
        return Illustration.objects.create(
            message=message,
            prompt=prompt,
            status=status,
        )

    @database_sync_to_async
    def _build_image_prompt(self, content):
        return build_image_prompt(content)

    @database_sync_to_async
    def _generate_image(self, prompt):
        return generate_image(prompt)

    @database_sync_to_async
    def _save_illustration_image(self, illustration, png_bytes):
        from django.core.files.base import ContentFile
        illustration.image.save(f'{illustration.pk}.png', ContentFile(png_bytes), save=False)
        illustration.save()

    @database_sync_to_async
    def _create_explanation(self, message, text, difficulty):
        Explanation.objects.create(
            message=message,
            content=text,
            difficulty_level=difficulty,
        )

    @database_sync_to_async
    def _generate_explanation(self, content, difficulty):
        return generate_explanation(content, difficulty)

    # ------------------------------------------------------------------
    # Envoi
    # ------------------------------------------------------------------

    async def _send_json(self, data):
        await self.send_json(data)

    async def _send_error(self, msg_id, code, message, retryable=False):
        await self._send_json({
            'type': 'error',
            'id': msg_id,
            'created_at': self._now_iso(),
            'payload': {
                'code': code,
                'message': message,
                'retryable': retryable,
            },
        })

    def _now_iso(self):
        return django_timezone.now().isoformat()
