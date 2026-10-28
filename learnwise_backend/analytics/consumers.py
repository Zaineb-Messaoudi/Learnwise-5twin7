import json
import logging
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class ProgressConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket pour la synchronisation de progression en temps real.

    Route : /ws/progress/{user_id}/
    """

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'progress_user_{self.user_id}'

        user = await self._authenticate()
        if user is None:
            await self.close(code=4001)
            return

        self.user = user

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')
        if msg_type == 'ping':
            await self.send_json({'type': 'pong'})
        else:
            await self.send_json({'type': 'error', 'message': 'Type non supporte.'})

    async def _authenticate(self):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken

        token = None
        query_string = self.scope.get('query_string', b'').decode()
        for part in query_string.split('&'):
            if part.startswith('token='):
                token = part.split('=', 1)[1]
                break

        if not token:
            return None

        try:
            validated = JWTAuthentication().get_validated_token(token)
            user = await database_sync_to_async(JWTAuthentication().get_user)(validated)
            return user
        except (InvalidToken, Exception):
            return None

class AnalyticsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
        self.group_name = f"analytics_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected"})
    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
    async def analytics_event(self, event):
        await self.send_json({"event": event["event"], "data": event["payload"]})


class LegacyProgressConsumer(AnalyticsConsumer):
    """Temporary adapter for clients released before /ws/analytics/."""

    EVENT_TYPES = {
        "progress.updated": "progress_update",
        "achievement.earned": "achievement_unlocked",
        "session.updated": "session_update",
        "quiz.available": "quiz_available",
        "material.ready": "material_ready",
    }

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        # Never trust the id embedded by this legacy client. The JWT identity
        # alone determines the private channel group, preventing cross-user
        # subscriptions while remaining compatible with stale URL values.
        self.group_name = f"analytics_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected"})

    async def analytics_event(self, event):
        payload = dict(event["payload"])
        event_type = self.EVENT_TYPES.get(event["event"], event["event"])
        if event_type == "progress_update" and "completion_percentage" in payload:
            payload["progress"] = float(payload["completion_percentage"]) / 100
        await self.send_json({"type": event_type, **payload})
