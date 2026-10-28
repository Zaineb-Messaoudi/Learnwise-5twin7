from channels.generic.websocket import AsyncJsonWebsocketConsumer

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
