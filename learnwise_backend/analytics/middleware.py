from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

@database_sync_to_async
def _user_for_token(raw_token):
    try:
        authentication = JWTAuthentication()
        validated = authentication.get_validated_token(raw_token)
        return authentication.get_user(validated)
    except Exception:
        return AnonymousUser()

class QueryStringJWTAuthMiddleware:
    """Authenticate browser WebSockets because their API cannot set headers."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        if query.get("token"):
            scope["user"] = await _user_for_token(query["token"][0])
        return await self.app(scope, receive, send)
