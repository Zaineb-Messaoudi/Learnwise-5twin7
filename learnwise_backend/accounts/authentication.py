"""
Session-aware JWT authentication.

Every token pair issued at login carries a ``sid`` claim that points to a
``UserSession`` row. When that session is revoked (user clicked "revoke",
logged out, changed password, an admin locked the account...) the access token
is rejected immediately and the refresh token can no longer be exchanged for a
new access token.

NOTE: this module is imported eagerly by Django as soon as anything touches
`rest_framework.views` (DRF resolves DEFAULT_AUTHENTICATION_CLASSES from
settings very early, inside rest_framework.schemas). Do NOT import anything
here that pulls in rest_framework.generics/views (e.g.
rest_framework_simplejwt.views) or you will hit a circular import. The
TokenRefreshView subclass that needs that import lives in views.py instead,
which is only imported later via urls.py.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

# Update UserSession.last_activity at most this often (avoids a write per request)
SESSION_TOUCH_INTERVAL = timedelta(minutes=5)


def is_session_revoked(sid):
    """True if a session id (``sid`` claim) belongs to a revoked session."""
    if not sid:
        return False
    from .models import UserSession
    return UserSession.objects.filter(session_key=sid, revoked_at__isnull=False).exists()


class SessionAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        sid = validated_token.get('sid')
        if sid:
            from .models import UserSession
            row = UserSession.objects.filter(session_key=sid).values('revoked_at', 'last_activity').first()
            if row is not None:
                if row['revoked_at'] is not None:
                    raise AuthenticationFailed('This session has been revoked.', code='session_revoked')
                now = timezone.now()
                if row['last_activity'] is None or now - row['last_activity'] > SESSION_TOUCH_INTERVAL:
                    UserSession.objects.filter(session_key=sid, revoked_at__isnull=True).update(last_activity=now)
        return user


class SessionAwareTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs['refresh'])
        except TokenError as exc:
            raise InvalidToken(exc.args[0])
        if is_session_revoked(refresh.get('sid')):
            raise InvalidToken('This session has been revoked.')
        try:
            data = super().validate(attrs)
        except get_user_model().DoesNotExist:
            raise InvalidToken('User no longer exists.')

        # "Remember me" sessions keep their longer lifetime when the token rotates
        if refresh.get('rm') and data.get('refresh'):
            days = getattr(settings, 'REMEMBER_ME_REFRESH_DAYS', 30)
            rotated = RefreshToken(data['refresh'])
            rotated.set_exp(lifetime=timedelta(days=days))
            data['refresh'] = str(rotated)
        return data
