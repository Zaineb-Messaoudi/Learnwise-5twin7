import json
import base64
from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

User = get_user_model()

from content.models import Course, CoursePresence
from ai_assistant.models import AssistantSession


class PresenceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time course presence.

    Clients connect to: ws://host/ws/content/courses/{course_id}/presence/
    Message format: {"type": "join"} or {"type": "leave"}

    On join: adds user to course presence group, creates CoursePresence row,
             broadcasts updated presence list to all group members.
    On leave/ disconnect: removes user from presence, broadcasts update.
    """

    async def connect(self):
        self.course_id = self.scope['url_route']['kwargs']['course_id']
        self.group_name = f'course_presence_{self.course_id}'

        # Authenticate via JWT token from query string
        jwt_auth = JWTAuthentication()
        query_string = self.scope.get('query_string', b'').decode()
        query_params = {}
        if query_string:
            for part in query_string.split('&'):
                if '=' in part:
                    k, v = part.split('=', 1)
                    query_params[k] = v
        token = query_params.get('token')
        if token:
            try:
                validated_token = jwt_auth.get_validated_token(token)
                user_id = validated_token['user_id']
                get_user = sync_to_async(User.objects.get)
                user = await get_user(user_id)
                self.scope['user'] = user
            except (InvalidToken, TokenError, User.DoesNotExist):
                pass

        self.user = self.scope['user']

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Verify course exists
        try:
            self.course = await sync_to_async(Course.objects.get)(id=self.course_id)
        except Course.DoesNotExist:
            await self.close(code=4004)
            return

        # Join room group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Create or update presence record
        await self._upsert_presence()

        # Broadcast updated presence list
        await self._broadcast_presence()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            if hasattr(self, 'user') and self.user.is_authenticated:
                await self._remove_presence()
                await self._broadcast_presence()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'join':
            await self._upsert_presence()
            await self._broadcast_presence()
        elif msg_type == 'leave':
            await self._remove_presence()
            await self._broadcast_presence()
        elif msg_type == 'heartbeat':
            await self._touch_presence()

    async def presence_update(self, event):
        """Sent by group when presence changes."""
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'course_id': self.course_id,
            'users': event['users'],
            'count': event['count'],
        }))

    # --- Helpers ---

    @sync_to_async
    def _upsert_presence(self):
        CoursePresence.objects.update_or_create(
            course=self.course,
            user=self.user,
            defaults={
                'channel_name': self.channel_name,
                'last_seen': timezone.now(),
            },
        )

    @sync_to_async
    def _remove_presence(self):
        CoursePresence.objects.filter(course=self.course, user=self.user).delete()

    @sync_to_async
    def _touch_presence(self):
        CoursePresence.objects.filter(course=self.course, user=self.user).update(
            last_seen=timezone.now()
        )

    @sync_to_async
    def _get_presence_list(self):
        presences = CoursePresence.objects.filter(
            course=self.course
        ).select_related('user').order_by('-last_seen')
        return [
            {
                'user_id': p.user.id,
                'email': p.user.email,
                'name': p.user.name if hasattr(p.user, 'name') else f'{p.user.first_name} {p.user.last_name}'.strip() or p.user.email,
                'role': p.user.role,
                'joined_at': p.joined_at.isoformat(),
                'last_seen': p.last_seen.isoformat(),
            }
            for p in presences
        ]

    async def _broadcast_presence(self):
        users = await self._get_presence_list()
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'presence_update',
                'users': users,
                'count': len(users),
            },
        )


class ProgressConsumer(AsyncWebsocketConsumer):
    """WebSocket for real-time progress updates on a user's courses."""

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'progress_{self.user_id}'

        jwt_auth = JWTAuthentication()
        query_string = self.scope.get('query_string', b'').decode()
        query_params = {}
        if query_string:
            for part in query_string.split('&'):
                if '=' in part:
                    k, v = part.split('=', 1)
                    query_params[k] = v
        token = query_params.get('token')
        if token:
            try:
                validated_token = jwt_auth.get_validated_token(token)
                uid = validated_token['user_id']
                get_user = sync_to_async(User.objects.get)
                user = await get_user(uid)
                self.scope['user'] = user
            except (InvalidToken, TokenError, User.DoesNotExist):
                pass

        self.user = self.scope['user']

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Only allow connecting to your own progress stream
        if str(self.user.id) != self.user_id:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        # Echo progress updates back to the client (placeholder for real logic)
        msg_type = data.get('type')
        if msg_type == 'heartbeat':
            await self.send(text_data=json.dumps({'type': 'heartbeat_ack'}))

    async def progress_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'course_id': event.get('course_id'),
            'progress': event.get('progress'),
        }))


class AssistantConsumer(AsyncWebsocketConsumer):
    """WebSocket for AI assistant chat within a session."""

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f'assistant_{self.session_id}'

        jwt_auth = JWTAuthentication()
        query_string = self.scope.get('query_string', b'').decode()
        query_params = {}
        if query_string:
            for part in query_string.split('&'):
                if '=' in part:
                    k, v = part.split('=', 1)
                    query_params[k] = v
        token = query_params.get('token')
        if token:
            try:
                validated_token = jwt_auth.get_validated_token(token)
                uid = validated_token['user_id']
                get_user = sync_to_async(User.objects.get)
                user = await get_user(uid)
                self.scope['user'] = user
            except (InvalidToken, TokenError, User.DoesNotExist):
                pass

        self.user = self.scope['user']

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Verify session belongs to user
        try:
            session = await sync_to_async(AssistantSession.objects.select_related('user').get)(
                id=self.session_id
            )
        except AssistantSession.DoesNotExist:
            await self.close(code=4004)
            return

        if session.user_id != self.user.id:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        msg_type = data.get('type')
        if msg_type == 'heartbeat':
            await self.send(text_data=json.dumps({'type': 'heartbeat_ack'}))
        elif msg_type == 'message':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'assistant_message',
                    'content': data.get('content', ''),
                    'session_id': self.session_id,
                    'user_id': self.user.id,
                },
            )

    async def assistant_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'assistant_message',
            'content': event['content'],
            'session_id': event['session_id'],
            'user_id': event['user_id'],
        }))
