import io
import json
import uuid
import secrets
import base64
import hashlib
import logging
import qrcode
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.http import FileResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, permissions, generics, serializers
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from .permissions import IsAdmin
from .authentication import SessionAwareTokenRefreshSerializer

from .models import (
    EmailVerification,
    PasswordResetToken,
    SocialAccount,
    UserSession,
    SecurityEvent,
    ActivityLog,
    DataExportRequest,
    AccountDeletionRequest,
    TermsVersion,
    FaceProfile,
)
from .serializers import (
    AccountDeletionConfirmSerializer,
    AccountDeletionCreateSerializer,
    AdminUserCreateSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    DataExportCreateSerializer,
    DataExportRequestSerializer,
    EmailChangeConfirmSerializer,
    EmailChangeRequestSerializer,
    EmailVerificationSerializer,
    EmailVerifyCodeSerializer,
    FaceProfileSerializer,
    FaceRegistrationSerializer,
    FaceVerificationSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SelectRoleSerializer,
    SocialAccountSerializer,
    SocialAuthSerializer,
    TermsVersionSerializer,
    TermsAcceptSerializer,
    TwoFactorDisableSerializer,
    TwoFactorSetupSerializer,
    TwoFactorVerifySerializer,
    UserSerializer,
    UserProfileSerializer,
    UserSessionSerializer,
    SecurityEventSerializer,
    ActivityLogSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def get_tokens_for_user(user, request=None, remember_me=False, auth_method='password'):
    """Issue a refresh/access pair.

    When a request is given, a UserSession row is created and its id is embedded
    in the tokens as the ``sid`` claim, so the session can be revoked server-side.
    ``remember_me`` gives the refresh token a longer lifetime and marks it with the
    ``rm`` claim so that the longer lifetime survives token rotation.
    ``auth_method`` records how the user authenticated (password / face / social)
    so sensitive operations can require step-up re-authentication.
    """
    refresh = RefreshToken.for_user(user)
    refresh['auth_method'] = auth_method
    if remember_me:
        refresh['rm'] = True
        refresh.set_exp(lifetime=timedelta(days=getattr(settings, 'REMEMBER_ME_REFRESH_DAYS', 30)))
    if request is not None:
        sid = secrets.token_hex(16)
        refresh['sid'] = sid
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        try:
            UserSession.objects.create(
                user=user,
                session_key=sid,
                auth_method=auth_method,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=user_agent,
                device_info=parse_user_agent(user_agent),
                is_current=True,
            )
        except Exception:
            logger.exception('Could not create session record')
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_current_sid(request):
    """Session id (``sid`` claim) of the token used for this request, if any."""
    auth = getattr(request, 'auth', None)
    try:
        return auth.get('sid') if auth is not None else None
    except Exception:
        return None


def revoke_user_sessions(user, except_sid=None, blacklist_tokens=False):
    """Revoke a user's sessions. With blacklist_tokens=True every outstanding
    refresh token is blacklisted too (also covers tokens without a session)."""
    sessions = user.sessions.filter(revoked_at__isnull=True)
    if except_sid:
        sessions = sessions.exclude(session_key=except_sid)
    count = sessions.update(revoked_at=timezone.now(), is_current=False)
    if blacklist_tokens:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
    return count


def log_security_event(user, event_type, severity='info', description='', metadata=None, ip_address=None, user_agent=''):
    SecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        severity=severity,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
    )


def require_step_up(request):
    """Return a 403 response if the current session was established by face
    recognition (weaker than password + 2FA, no liveness). Sensitive operations
    (password change, email change, account deletion, 2FA disable) must be
    re-authenticated with a password first."""
    token = getattr(request, 'auth', None)
    auth_method = token.get('auth_method') if token is not None else None
    if auth_method == 'face':
        return Response(
            {'detail': 'Please re-authenticate with your password before performing this action.', 'requires_step_up': True},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def log_activity(user, action, resource_type, resource_id='', description='', ip_address=None, user_agent=''):
    ActivityLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'register'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        log_security_event(
            user=user,
            event_type='login',
            severity='info',
            description='Account created successfully',
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Send the verification email (login is blocked until the email is verified)
        try:
            ResendVerificationView()._send_verification_email(user, user.email_verification)
        except Exception:
            logger.exception('Could not send verification email after registration')

        # Do not issue tokens yet: the account is unverified until the email link is used.
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'detail': 'Account created. Please check your email to verify your address before logging in.',
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        totp_token = serializer.validated_data.get('totp_token')
        backup_code = serializer.validated_data.get('backup_code')

        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify the password BEFORE revealing any account state (lock status, etc.),
        # so a wrong guess never confirms whether an account exists or is locked.
        if not user.check_password(password):
            user.record_failed_login()
            log_security_event(
                user=user,
                event_type='login_failed',
                severity='warning',
                description=f'Failed login attempt: {user.failed_login_attempts} attempts',
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={'attempts': user.failed_login_attempts},
            )
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Password is correct — safe to reveal account-specific state now.
        if user.is_locked():
            return Response(
                {'detail': 'Your account has been temporarily locked due to multiple failed login attempts. Please try again later.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not user.is_active:
            return Response({'detail': 'This account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)

        # Email verification required for normal signup
        if not user.email_verified:
            return Response(
                {'detail': 'Please verify your email address before logging in. Check your inbox for the verification link.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2FA check
        if user.two_factor_enabled:
            if not totp_token and not backup_code:
                return Response(
                    {'detail': 'Two-factor authentication is enabled. Please provide a TOTP token or backup code.', 'requires_2fa': True},
                    status=status.HTTP_428_PRECONDITION_REQUIRED
                )

            verified = False
            if totp_token and user.verify_totp(totp_token):
                verified = True
            elif backup_code and user.use_backup_code(backup_code):
                verified = True

            if not verified:
                # Failed 2FA attempts count toward the account lockout
                user.record_failed_login()
                log_security_event(
                    user=user,
                    event_type='login_failed',
                    severity='warning',
                    description='Failed 2FA verification',
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                return Response({'detail': 'Invalid 2FA token.', 'requires_2fa': True}, status=status.HTTP_401_UNAUTHORIZED)

        user.record_successful_login()

        log_security_event(
            user=user,
            event_type='login',
            severity='info',
            description='Successful login',
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={'remember_me': serializer.validated_data.get('remember_me', False)},
        )

        tokens = get_tokens_for_user(user, request, remember_me=serializer.validated_data.get('remember_me', False))
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        })


def parse_user_agent(user_agent):
    """Simple user agent parser."""
    if not user_agent:
        return {'browser': 'Unknown', 'os': 'Unknown', 'device_type': 'desktop'}

    is_mobile = 'mobile' in user_agent.lower()
    is_tablet = 'tablet' in user_agent.lower()
    device_type = 'mobile' if is_mobile else ('tablet' if is_tablet else 'desktop')

    browser = 'Unknown'
    if 'Chrome' in user_agent:
        browser = 'Chrome'
    elif 'Firefox' in user_agent:
        browser = 'Firefox'
    elif 'Safari' in user_agent:
        browser = 'Safari'
    elif 'Edge' in user_agent:
        browser = 'Edge'

    os_name = 'Unknown'
    if 'Windows' in user_agent:
        os_name = 'Windows'
    elif 'Mac OS' in user_agent:
        os_name = 'macOS'
    elif 'Linux' in user_agent:
        os_name = 'Linux'
    elif 'Android' in user_agent:
        os_name = 'Android'
    elif 'iOS' in user_agent:
        os_name = 'iOS'

    return {'browser': browser, 'os': os_name, 'device_type': device_type}


class SessionAwareTokenRefreshView(TokenRefreshView):
    """TokenRefreshView that rejects refresh tokens belonging to a revoked
    session (sid claim). Lives here, not in authentication.py, to avoid a
    circular import (see the note at the top of authentication.py)."""
    serializer_class = SessionAwareTokenRefreshSerializer
    # Refresh calls are anonymous (no access token yet); give them their own bucket
    # instead of the shared per-IP anonymous quota.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'token_refresh'


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except (TokenError, InvalidToken):
                pass
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        log_security_event(
            user=request.user,
            event_type='logout',
            severity='info',
            description='User logged out',
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Revoke the session this token belongs to
        sid = get_current_sid(request)
        if sid:
            request.user.sessions.filter(session_key=sid, revoked_at__isnull=True).update(
                revoked_at=timezone.now(), is_current=False
            )

        return Response({'detail': 'Successfully logged out.'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        ip_address = request.META.get('REMOTE_ADDR')
        log_security_event(
            user=request.user,
            event_type='profile_updated',
            severity='info',
            description='Profile updated',
            ip_address=ip_address,
        )
        log_activity(
            user=request.user,
            action='update',
            resource_type='profile',
            description='Profile information updated',
            ip_address=ip_address,
        )

        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        step_up = require_step_up(request)
        if step_up:
            return step_up
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data['new_password']

        # Add old password to history before changing
        old_password_hash = user.password
        user.set_password(new_password)
        user.save()

        # Add old password to history
        user.add_password_to_history(old_password_hash)

        # Sign out every other device (the current session stays valid)
        revoke_user_sessions(user, except_sid=get_current_sid(request))

        ip_address = request.META.get('REMOTE_ADDR')
        log_security_event(
            user=user,
            event_type='password_change',
            severity='info',
            description='Password changed successfully',
            ip_address=ip_address,
        )

        return Response({'detail': 'Password changed successfully.'})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()

        # Same response whether or not the account exists (no user enumeration)
        generic_response = Response({'detail': 'If an account exists for that email, a reset link will be sent.'})

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            return generic_response

        # Invalidate previously issued, still unused reset links
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        reset_token = PasswordResetToken.objects.create(user=user)

        reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token.token}"
        self._send_reset_email(user, reset_link)

        log_security_event(
            user=user,
            event_type='password_change',
            severity='info',
            description='Password reset requested',
        )

        return generic_response


    def _send_reset_email(self, user, reset_link):
        subject = 'Reset your Learnwise password'
        message = f'''Hello {user.first_name or user.email},

You requested a password reset for your Learnwise account.

Click the link below to set a new password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
The Learnwise Team'''

        try:
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            else:
                logger.info(f"[DEV EMAIL] To: {user.email}, Subject: {subject}, Message: {message}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            reset_token = PasswordResetToken.objects.get(token=token_str)
        except (PasswordResetToken.DoesNotExist, ValueError, DjangoValidationError):
            return Response({'detail': 'Invalid or expired reset token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not reset_token.is_valid():
            return Response({'detail': 'This reset link has expired or has already been used.'}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user

        # Check password history
        if user.check_password_history(password):
            return Response({'detail': 'This password was recently used. Please choose a different one.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save old password hash before changing
        old_hash = user.password
        user.set_password(password)
        user.save()
        user.add_password_to_history(old_hash)
        reset_token.mark_used()

        # Invalidate any other outstanding reset links and sign out everywhere
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        revoke_user_sessions(user, blacklist_tokens=True)

        log_security_event(
            user=user,
            event_type='password_change',
            severity='info',
            description='Password reset via email link',
        )

        return Response({'detail': 'Password has been reset successfully.'})


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            verification = EmailVerification.objects.get(token=token)
        except (EmailVerification.DoesNotExist, ValueError, DjangoValidationError):
            return Response({'detail': 'Invalid verification token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not verification.is_valid():
            return Response({'detail': 'This verification link has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        if not verification.user.is_active:
            return Response({'detail': 'This account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)

        verification.mark_verified()
        tokens = get_tokens_for_user(verification.user, request)

        log_security_event(
            user=verification.user,
            event_type='profile_updated',
            severity='info',
            description='Email verified successfully',
        )

        return Response({
            'detail': 'Email verified successfully.',
            'user': UserSerializer(verification.user, context={'request': request}).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        })


class VerifyCodeView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'verify_code'

    def post(self, request):
        serializer = EmailVerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']
        email = serializer.validated_data['email'].lower()

        try:
            verification = EmailVerification.objects.get(code=code, user__email__iexact=email)
        except EmailVerification.DoesNotExist:
            return Response({'detail': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)
        except EmailVerification.MultipleObjectsReturned:
            EmailVerification.objects.filter(code=code, user__email__iexact=email).exclude(
                id=EmailVerification.objects.filter(code=code, user__email__iexact=email).first().id
            ).delete()
            verification = EmailVerification.objects.get(code=code, user__email__iexact=email)

        if not verification.is_valid():
            return Response({'detail': 'This verification code has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        if not verification.user.is_active:
            return Response({'detail': 'This account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)

        verification.mark_verified()
        tokens = get_tokens_for_user(verification.user, request)

        log_security_event(
            user=verification.user,
            event_type='profile_updated',
            severity='info',
            description='Email verified via code',
        )

        return Response({
            'detail': 'Email verified successfully.',
            'user': UserSerializer(verification.user, context={'request': request}).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        })


class ResendVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.email_verified:
            return Response({'detail': 'Email is already verified.'})

        verification, created = EmailVerification.objects.get_or_create(user=user)
        if not created and not verification.is_valid():
            verification.token = uuid.uuid4()
            verification.created_at = timezone.now()
            verification.verified_at = None
        verification.generate_code()
        verification.save()

        self._send_verification_email(user, verification)

        return Response({'detail': 'Verification email sent.'})

    def _send_verification_email(self, user, verification):
        verification_link = f"{settings.FRONTEND_URL}/auth/verify?token={verification.token}"
        subject = 'Verify your Learnwise email address'
        first_name = user.first_name or 'there'
        plain_message = f'''Hello {first_name},

Welcome to Learnwise! Please verify your email address by clicking the link below:

{verification_link}

Or enter this 6-digit code: {verification.code}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
The Learnwise Team'''

        html_message = f'''<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  </head>
  <body style="margin:0;padding:0;background:#f8faff;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#52618a;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8faff;">
      <tr>
        <td align="center" style="padding:40px 20px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;background:linear-gradient(160deg,#ffffff 0%,#f4f7ff 100%);border:1px solid #dbe4ff;border-radius:24px;box-shadow:0 24px 60px -16px rgba(23,32,92,0.16),0 0 0 1px rgba(87,216,255,0.12) inset;">
            <tr>
              <td align="center" style="padding:44px 32px 28px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center">
                      <div style="display:inline-flex;align-items:center;gap:10px;">
                        <div style="width:34px;height:34px;background:linear-gradient(135deg,#57d8ff,#ff4f87);border-radius:10px;display:grid;place-items:center;box-shadow:0 0 20px rgba(87,216,255,0.45);">
                          <span style="color:#17205c;font-size:16px;font-weight:900;letter-spacing:-1px;">L</span>
                        </div>
                        <span style="color:#17205c;font-size:20px;font-weight:800;letter-spacing:-0.5px;">Learnwise</span>
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:0 32px 34px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center">
                      <div style="width:72px;height:72px;background:rgba(87,216,255,0.12);border:1px solid rgba(87,216,255,0.35);border-radius:20px;display:grid;place-items:center;box-shadow:0 0 30px rgba(87,216,255,0.3);">
                        <span style="color:#57d8ff;font-size:30px;">@</span>
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:0 32px 10px;">
                <h1 style="margin:0 0 10px;font-size:27px;line-height:1.25;color:#17205c;font-weight:800;letter-spacing:-0.5px;">Verify your email</h1>
                <p style="margin:0 0 26px;font-size:15px;line-height:1.6;color:#52618a;">Welcome to Learnwise, <strong style="color:#17205c;">{first_name}</strong>! Confirm your email to activate your account.</p>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 32px 30px;">
                  <tr>
                    <td align="center">
                      <a href="{verification_link}" style="display:inline-block;width:auto;background:linear-gradient(135deg,#2848d8,#17205c);color:#fff;font-size:15px;font-weight:800;text-decoration:none;border-radius:14px;padding:16px 32px;box-shadow:0 18px 40px rgba(40,72,216,0.4);letter-spacing:-0.2px;">Verify email address</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:0 32px 16px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center" style="padding:0 10px;">
                      <div style="font-size:12px;color:#52618a;">Or enter code:</div>
                      <div style="display:flex;justify-content:center;gap:6px;margin-top:6px;">
                        {''.join(f'<span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;background:#ffffff;border:1px solid #dbe4ff;color:#17205c;font-size:14px;font-weight:800;border-radius:8px;letter-spacing:0.5px;">{ch}</span>' for ch in verification.code)}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:24px 32px 44px;">
                <p style="margin:0 0 8px;font-size:12px;line-height:1.6;color:#52618a;">This link expires in 24 hours.</p>
                <p style="margin:0;font-size:12px;line-height:1.6;color:#52618a;">If you didn&rsquo;t create this account, you can safely ignore this email.</p>
                <p style="margin:20px 0 0;font-size:12px;line-height:1.6;color:#52618a;">Best regards,<br/><span style="color:#17205c;">The Learnwise Team</span></p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>'''

        try:
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                msg = EmailMultiAlternatives(
                    subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email],
                )
                msg.attach_alternative(html_message, 'text/html')
                msg.send(fail_silently=False)
            else:
                logger.info(f"[DEV EMAIL] To: {user.email}, Subject: {subject}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")


class PublicResendVerificationView(APIView):
    """Lets a user who cannot sign in yet (email not verified) ask for a fresh
    verification link. Public + throttled + non-enumerating: the response is
    identical whether or not the address exists."""
    permission_classes = [AllowAny]
    throttle_scope = 'resend_verification'

    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        generic = Response({'detail': 'If that account exists and is not verified yet, a new verification link has been sent.'})
        if not email:
            return generic
        user = User.objects.filter(email__iexact=email, is_active=True, email_verified=False).first()
        if user is None:
            return generic

        verification, created = EmailVerification.objects.get_or_create(user=user)
        if not created and not verification.is_valid():
            verification.token = uuid.uuid4()
            verification.created_at = timezone.now()
            verification.verified_at = None
            verification.save()
        verification.generate_code()
        verification.save()
        ResendVerificationView()._send_verification_email(user, verification)
        return generic


class SocialAuthView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'social'

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data.get('access_token')
        code = serializer.validated_data.get('code')
        role = serializer.validated_data.get('role')

        if code and not access_token:
            try:
                if provider == 'google':
                    access_token = self._exchange_google_code(code)
                elif provider == 'facebook':
                    access_token = self._exchange_facebook_code(code)
                else:
                    return Response({'detail': 'Unsupported provider.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"OAuth code exchange failed for {provider}: {e}")
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if not access_token:
                return Response({'detail': 'Failed to exchange authorization code.'}, status=status.HTTP_400_BAD_REQUEST)

        if not access_token:
            return Response({'detail': 'Access token or authorization code required.'}, status=status.HTTP_400_BAD_REQUEST)

        if provider == 'google':
            user_data = self._verify_google_token(access_token)
        elif provider == 'facebook':
            user_data = self._verify_facebook_token(access_token)
        else:
            return Response({'detail': 'Unsupported provider.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user_data:
            return Response({'detail': 'Invalid social token.'}, status=status.HTTP_400_BAD_REQUEST)

        email = user_data.get('email', '').lower()
        if not email:
            return Response({'detail': 'Email not provided by social provider.'}, status=status.HTTP_400_BAD_REQUEST)

        # Require verified email from provider
        if provider == 'google' and not user_data.get('email_verified', False):
            return Response({'detail': 'Google account email not verified.'}, status=status.HTTP_400_BAD_REQUEST)
        # Facebook does not return an email_verified field; if email is present it is verified by Facebook

        with transaction.atomic():
            try:
                user = User.objects.get(email=email)
                # Pre-hijack protection: if an account with a password already exists
                # for this email AND no social account is linked for this provider,
                # social login cannot take it over. The user must sign in with their
                # password first, then link the social account.
                if user.has_usable_password():
                    existing_social = SocialAccount.objects.filter(user=user, provider=provider).first()
                    if not existing_social:
                        return Response({
                            'detail': 'An account with this email already exists. Please sign in with your password, then link your social account.',
                            'requires_password_login': True,
                        }, status=status.HTTP_409_CONFLICT)
                created = False
            except User.DoesNotExist:
                user = User.objects.create(
                    email=email,
                    username=self._unique_username(email),
                    first_name=user_data.get('given_name', user_data.get('first_name', '')),
                    last_name=user_data.get('family_name', user_data.get('last_name', '')),
                    role=None,
                    email_verified=True,
                )
                user.set_unusable_password()
                user.save()
                created = True
                try:
                    EmailVerification.objects.get_or_create(user=user)
                except EmailVerification.DoesNotExist:
                    pass
                log_security_event(
                    user=user,
                    event_type='login',
                    severity='info',
                    description=f'Account created via {provider} OAuth',
                )
            else:
                # Verify social account belongs to this user, or link it if not yet connected
                social_account = SocialAccount.objects.filter(user=user, provider=provider).first()
                if not social_account:
                    # Link the social account to the existing user
                    # The user has proven email ownership via the OAuth provider
                    social_account = SocialAccount.objects.create(
                        user=user,
                        provider=provider,
                        provider_user_id=str(user_data.get('sub', user_data.get('id'))),
                        access_token='',
                    )
                    log_security_event(
                        user=user,
                        event_type='social_account_linked',
                        severity='info',
                        description=f'Linked {provider} account to existing email/password account',
                    )
                elif social_account.provider_user_id != str(user_data.get('sub', user_data.get('id'))):
                    return Response({'detail': 'This social account does not match the linked account.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    log_security_event(
                        user=user,
                        event_type='login',
                        severity='info',
                        description=f'Login via {provider} OAuth',
                    )

                if not user.is_active:
                    return Response({'detail': 'This account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)
                if user.is_locked():
                    return Response({'detail': 'This account is temporarily locked.'}, status=status.HTTP_403_FORBIDDEN)

                # The provider access token is not needed after verification, so it is not stored
                SocialAccount.objects.update_or_create(
                    user=user,
                    provider=provider,
                    defaults={
                        'provider_user_id': str(user_data.get('sub', user_data.get('id'))),
                        'access_token': '',
                    }
                )

        if not user.is_active:
            return Response({'detail': 'This account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)
        if user.is_locked():
            return Response({'detail': 'Your account is temporarily locked.'}, status=status.HTTP_403_FORBIDDEN)

        # The provider access token is not needed after verification, so it is not stored
        SocialAccount.objects.update_or_create(
            user=user,
            provider=provider,
            defaults={
                'provider_user_id': str(user_data.get('sub', user_data.get('id'))),
                'access_token': '',
            }
        )

        # Role can be supplied inline on first social sign-up, OR picked afterwards via
        # SelectRoleView; this also lets an *existing* social account that still has no
        # role (role selection was skipped/abandoned) pick one up on a later login.
        if role and user.role is None:
            user.role = role
            user.save(update_fields=['role'])

        # If 2FA is enabled the client must send a TOTP/backup code together with the social token
        if user.two_factor_enabled:
            totp_token = serializer.validated_data.get('totp_token')
            backup_code = serializer.validated_data.get('backup_code')
            if not totp_token and not backup_code:
                return Response({
                    'detail': 'Two-factor authentication required.',
                    'requires_2fa': True,
                }, status=status.HTTP_428_PRECONDITION_REQUIRED)

            verified = bool(totp_token and user.verify_totp(totp_token)) or bool(backup_code and user.use_backup_code(backup_code))
            if not verified:
                user.record_failed_login()
                log_security_event(
                    user=user,
                    event_type='login_failed',
                    severity='warning',
                    description='Failed 2FA verification (social login)',
                )
                return Response({'detail': 'Invalid 2FA token.', 'requires_2fa': True}, status=status.HTTP_401_UNAUTHORIZED)

        tokens = get_tokens_for_user(user, request)

        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'is_new_user': created,
            # Kept for backward compatibility with older frontend builds;
            # prefer the equivalent flags nested under `user` going forward.
            'needs_profile_completion': user.needs_onboarding(),
        })

    def _unique_username(self, email):
        base = (email.split('@')[0] or 'user')[:130]
        candidate = base
        while User.objects.filter(username__iexact=candidate).exists():
            candidate = f"{base}{secrets.token_hex(2)}"
        return candidate

    def _exchange_google_code(self, code):
        import requests
        try:
            redirect_uri = settings.GOOGLE_CALLBACK_URL
            logger.info(f"Google OAuth: Exchanging code with redirect_uri={redirect_uri}")
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri,
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                error_data = response.json()
                logger.error(f"Google token exchange failed: {error_data}")
                raise Exception(f"Google OAuth error: {error_data.get('error', 'unknown')} - {error_data.get('error_description', 'No description')}")
        except Exception as e:
            logger.error(f"Google code exchange failed: {e}")
            raise

    def _exchange_facebook_code(self, code):
        import requests
        try:
            redirect_uri = settings.FACEBOOK_CALLBACK_URL
            logger.info(f"Facebook OAuth: Exchanging code with redirect_uri={redirect_uri}")
            response = requests.get(
                'https://graph.facebook.com/v23.0/oauth/access_token',
                params={
                    'client_id': settings.FACEBOOK_APP_ID,
                    'client_secret': settings.FACEBOOK_APP_SECRET,
                    'code': code,
                    'redirect_uri': redirect_uri,
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                error_data = response.json()
                logger.error(f"Facebook token exchange failed: {error_data}")
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                raise Exception(f"Facebook OAuth error: {error_msg}")
        except Exception as e:
            logger.error(f"Facebook code exchange failed: {e}")
            raise

    def _verify_google_token(self, access_token):
        import requests
        try:
            # First verify the token info including audience
            tokeninfo_response = requests.get(
                'https://www.googleapis.com/oauth2/v3/tokeninfo',
                params={'access_token': access_token},
                timeout=10
            )
            if tokeninfo_response.status_code != 200:
                logger.error(f"Google tokeninfo failed: {tokeninfo_response.status_code} - {tokeninfo_response.text}")
                return None
            
            tokeninfo = tokeninfo_response.json()
            # Verify audience matches our client ID
            aud = tokeninfo.get('aud')
            if aud != settings.GOOGLE_CLIENT_ID:
                logger.error(f"Google token audience mismatch: expected {settings.GOOGLE_CLIENT_ID}, got {aud}")
                return None
            
            # Now get user info
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Google token verification successful")
                return user_data
            else:
                logger.error(f"Google token verification failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Google token verification failed: {e}")
        return None

    def _verify_facebook_token(self, access_token):
        import requests
        try:
            # Make sure the token was issued to OUR app (not another Facebook app)
            debug = requests.get(
                'https://graph.facebook.com/debug_token',
                params={
                    'input_token': access_token,
                    'access_token': f'{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}',
                },
                timeout=10,
            )
            debug_data = debug.json().get('data', {}) if debug.status_code == 200 else {}
            if not debug_data.get('is_valid') or str(debug_data.get('app_id')) != str(settings.FACEBOOK_APP_ID):
                logger.error('Facebook token is invalid or was not issued to this app')
                return None

            response = requests.get(
                'https://graph.facebook.com/me',
                params={
                    'fields': 'id,email,first_name,last_name',
                    'access_token': access_token
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Facebook token verification failed: {e}")
        return None


class SelectRoleView(APIView):
    """
    Step 1 of onboarding for accounts created with no role yet (mainly social
    sign-ups that skipped the inline role field). One-shot: once role is set
    it can't be changed here again — admin promotion/role changes go through
    the admin API instead.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SelectRoleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.role = serializer.validated_data['role']
        user.save(update_fields=['role'])

        log_security_event(
            user=user,
            event_type='profile_updated',
            severity='info',
            description=f'Role selected: {user.role}',
        )

        return Response(UserSerializer(user, context={'request': request}).data)


# Two-Factor Authentication Views
class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = '2fa'

    def get(self, request):
        user = request.user
        if user.two_factor_enabled:
            return Response({'detail': 'Two-factor authentication is already enabled.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.totp_secret:
            user.generate_totp_secret()
            user.refresh_from_db()

        # Backup codes are only generated (and shown once) when 2FA is actually enabled
        backup_codes = []

        totp = None
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        uri = totp.provisioning_uri(user.email, issuer_name='Learnwise')

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            'secret': user.totp_secret,
            'qr_code': f'data:image/png;base64,{img_base64}',
            'backup_codes': backup_codes,
        })

    def post(self, request):
        user = request.user
        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        backup_code = serializer.validated_data.get('backup_code')

        if user.two_factor_enabled:
            return Response({'detail': 'Two-factor authentication is already enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        # Enabling 2FA requires a valid authenticator code (backup codes are not accepted here)
        if not token or not user.verify_totp(token):
            raise serializers.ValidationError({'token': 'Invalid TOTP token.'})

        # Only hashes are stored; the plaintext codes are returned once below
        backup_codes = user.generate_backup_codes(10)

        user.two_factor_enabled = True
        user.save(update_fields=['two_factor_enabled'])

        log_security_event(
            user=user,
            event_type='2fa_enabled',
            severity='info',
            description='Two-factor authentication enabled',
        )

        return Response({
            'detail': 'Two-factor authentication enabled successfully.',
            'backup_codes': backup_codes,
        })


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = '2fa'

    def post(self, request):
        step_up = require_step_up(request)
        if step_up:
            return step_up
        user = request.user
        serializer = TwoFactorDisableSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user.two_factor_enabled = False
        user.totp_secret = ''
        user.backup_codes = []
        user.save(update_fields=['two_factor_enabled', 'totp_secret', 'backup_codes'])

        log_security_event(
            user=user,
            event_type='2fa_disabled',
            severity='info',
            description='Two-factor authentication disabled',
        )

        return Response({'detail': 'Two-factor authentication disabled successfully.'})


# Email Change Views
class EmailChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        step_up = require_step_up(request)
        if step_up:
            return step_up
        serializer = EmailChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data['new_email']

        user = request.user
        user.request_email_change(new_email)

        # Send email change verification
        change_link = f"{settings.FRONTEND_URL}/auth/email-change/confirm?token={user.email_change_token}"
        self._send_email_change_email(user, new_email, change_link)

        log_security_event(
            user=user,
            event_type='email_change_requested',
            severity='info',
            description=f'Email change requested from {user.email} to {new_email}',
        )

        return Response({'detail': 'Email change verification has been sent to the new email address.'})

    def _send_email_change_email(self, user, new_email, change_link):
        subject = 'Confirm your new email address'
        message = f'''Hello {user.first_name or user.email},

You requested to change your email address to {new_email}.

Please click the link below to confirm this change:
{change_link}

This link will expire in 24 hours.

If you didn't request this, please ignore this email.

Best regards,
The Learnwise Team'''

        try:
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_email], fail_silently=False)
            else:
                logger.info(f"[DEV EMAIL] To: {new_email}, Subject: {subject}, Message: {message}")
        except Exception as e:
            logger.error(f"Failed to send email change verification to {new_email}: {e}")


class EmailChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        step_up = require_step_up(request)
        if step_up:
            return step_up
        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_str = serializer.validated_data['token']

        user = request.user
        if user.email_change_token:
            try:
                token_uuid = uuid.UUID(token_str)
            except ValueError:
                return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
            if user.email_change_token == token_uuid:
                old_email = user.email
                if user.confirm_email_change(token_uuid):
                    log_security_event(
                        user=user,
                        event_type='email_changed',
                        severity='info',
                        description=f'Email changed from {old_email} to {user.email}',
                    )
                    revoke_user_sessions(user, blacklist_tokens=True)
                    return Response({'detail': 'Email changed successfully. You will need to sign in again.'})
                else:
                    return Response({'detail': 'Invalid or expired email change token.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


# Session Management Views
class UserSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = request.user.sessions.filter(revoked_at__isnull=True).order_by('-last_activity')
        return Response(UserSessionSerializer(
            sessions, many=True, context={'current_sid': get_current_sid(request)}
        ).data)


class RevokeSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = request.user.sessions.get(id=session_id, revoked_at__isnull=True)
        except UserSession.DoesNotExist:
            return Response({'detail': 'Session not found or already revoked.'}, status=status.HTTP_404_NOT_FOUND)

        session.revoke()
        device_info = session.device_info or {}
        device_name = f"{device_info.get('browser', 'Unknown')} on {device_info.get('os', 'Unknown')}"
        log_security_event(
            user=request.user,
            event_type='session_revoked',
            severity='info',
            description=f'Session revoked: {device_name}',
        )
        return Response({'detail': 'Session revoked successfully.'})


class RevokeAllSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = revoke_user_sessions(request.user, except_sid=get_current_sid(request))
        log_security_event(
            user=request.user,
            event_type='all_sessions_revoked',
            severity='warning',
            description=f'All other sessions revoked ({count} sessions)',
        )
        return Response({'detail': f'{count} sessions revoked successfully.'})


# Avatar Upload View
class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.avatar = serializer.validated_data['avatar']
        user.save()

        log_security_event(
            user=user,
            event_type='profile_updated',
            severity='info',
            description='Avatar updated',
        )
        log_activity(
            user=user,
            action='update',
            resource_type='profile',
            description='Avatar image updated',
        )

        return Response({'detail': 'Avatar uploaded successfully.', 'avatar_url': user.avatar.url})

    def delete(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
            log_security_event(
                user=user,
                event_type='profile_updated',
                severity='info',
                description='Avatar removed',
            )
        return Response({'detail': 'Avatar removed successfully.'})


class AvatarRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
            log_security_event(
                user=user,
                event_type='profile_updated',
                severity='info',
                description='Avatar removed',
            )
        return Response({'detail': 'Avatar removed successfully.'})


# Face Recognition
class FaceRegisterView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        user = request.user

        # Re-authentication: accounts that have a password must confirm it before a
        # face can be enrolled or replaced (a stolen access token alone must not be
        # enough to plant a face that later unlocks the account). Accounts created
        # through Google/Facebook have no usable password and are already
        # authenticated by their provider.
        if user.has_usable_password():
            password = request.data.get('password', '')
            if not password or not user.check_password(password):
                return Response({'detail': 'Password required for face registration.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        # Multipart clients send the 128 floats as one JSON-encoded string
        raw_descriptor = data.get('descriptor')
        if isinstance(raw_descriptor, str):
            try:
                parsed = json.loads(raw_descriptor)
            except ValueError:
                return Response({'descriptor': ['Descriptor must be a JSON array of 128 numbers.']}, status=status.HTTP_400_BAD_REQUEST)
            data = {'descriptor': parsed}
            if data_quality := request.data.get('quality_score'):
                data['quality_score'] = data_quality
            if 'enrollment_image' in request.FILES:
                data['enrollment_image'] = request.FILES['enrollment_image']

        serializer = FaceRegistrationSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        descriptor = serializer.validated_data['descriptor']
        quality_score = serializer.validated_data.get('quality_score', 0.0)
        enrollment_image = serializer.validated_data.get('enrollment_image')

        with transaction.atomic():
            face_profile, created = FaceProfile.objects.update_or_create(
                user=user,
                defaults={
                    'descriptor': descriptor,
                    'quality_score': quality_score,
                    'enrollment_image': enrollment_image,
                    'is_verified': True,
                    'verified_at': timezone.now(),
                }
            )

            log_security_event(
                user=user,
                event_type='face_registered',
                severity='info',
                description='Face profile registered',
            )

            return Response(
                FaceProfileSerializer(face_profile).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )


class FaceVerifyView(APIView):
    """
    Face verification login.

    Identifies the closest enrolled face below FACE_MATCH_THRESHOLD, then applies
    the same account checks as password login (active, not locked, email verified)
    and refuses accounts that have 2FA enabled (they must use password + TOTP).

    NOTE: face-api.js descriptors are produced client-side and there is no liveness
    check, so this method is weaker than password + 2FA. Consider disabling it for
    staff/admin accounts.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'face_verify'

    def post(self, request):
        serializer = FaceVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        live_descriptor = serializer.validated_data['descriptor']

        best_match = None
        best_distance = float('inf')

        # Find best match with strict threshold
        # NOTE: This is an O(n) scan over all verified face profiles.
        # For production scale (>10k users), replace with a vector database
        # (pgvector, Pinecone, Weaviate) for approximate nearest neighbor search.
        # We match against ALL roles here so that face_login_allowed() below can
        # correctly return 403 for admins/staff instead of a misleading 401.
        for face_profile in FaceProfile.objects.filter(
            is_verified=True
        ).select_related('user'):
            verified, distance = face_profile.verify_face(live_descriptor)
            if verified and distance < best_distance:
                best_distance = distance
                best_match = face_profile

        if not best_match:
            # No enrolled face matched. We cannot attribute this to a specific user,
            # so per-user lockout does not apply; the IP-scoped ``face_verify``
            # throttle (10/minute) is the rate limit for unknown faces.
            logger.warning('Face login failed: no matching profile (ip=%s)', request.META.get('REMOTE_ADDR'))
            return Response(
                {'detail': 'Face not recognized. Please use email/password login.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = best_match.user

        # Face sign-in is a convenience for students/professors only: descriptors are
        # computed in the browser and there is no liveness check, so it must never
        # unlock admin/staff accounts (they use password + 2FA).
        if not user.face_login_allowed():
            user.record_failed_face_login()
            log_security_event(
                user=user,
                event_type='face_login_failed',
                severity='warning',
                description='Face login refused: not allowed for this account type',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            return Response(
                {'detail': 'Face sign-in is not available for this account. Use email/password login.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Face-login lockout: repeated failed face attempts for this account lock
        # face sign-in (the account can still use email/password).
        if user.is_face_locked():
            log_security_event(
                user=user,
                event_type='face_login_failed',
                severity='warning',
                description='Face login refused: account face-locked',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            return Response(
                {'detail': 'Face sign-in is temporarily locked for this account. Use email/password login.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check account status
        if not user.is_active:
            user.record_failed_face_login()
            return Response({'detail': 'Account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)

        # Password lockout also blocks face sign-in.
        if user.is_locked():
            user.record_failed_face_login()
            return Response({'detail': 'Account is temporarily locked.'}, status=status.HTTP_403_FORBIDDEN)

        # Check 2FA if enabled
        if user.two_factor_enabled:
            user.record_failed_face_login()
            return Response(
                {'detail': 'Two-factor authentication required. Use email/password login.', 'requires_2fa': True},
                status=status.HTTP_428_PRECONDITION_REQUIRED
            )

        # Check email verified
        if not user.email_verified:
            user.record_failed_face_login()
            return Response({'detail': 'Email not verified.'}, status=status.HTTP_403_FORBIDDEN)

        # Successful face login: mark token as face-authenticated (step-up required
        # for sensitive operations) and reset the face failure counter.
        user.record_successful_face_login()

        log_security_event(
            user=user,
            event_type='login',
            severity='info',
            description='Face recognition login',
            metadata={'distance': best_distance},
        )

        tokens = get_tokens_for_user(user, request, auth_method='face')
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        })


class FaceProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            face_profile = request.user.face_profile
        except FaceProfile.DoesNotExist:
            return Response({'detail': 'No face profile registered.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(FaceProfileSerializer(face_profile).data)

    def delete(self, request):
        try:
            face_profile = request.user.face_profile
            face_profile.delete()
            log_security_event(
                user=request.user,
                event_type='profile_updated',
                severity='info',
                description='Face profile deleted',
            )
            return Response({'detail': 'Face profile deleted successfully.'})
        except FaceProfile.DoesNotExist:
            return Response({'detail': 'No face profile to delete.'}, status=status.HTTP_404_NOT_FOUND)


# Social Accounts
class SocialAccountListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = request.user.social_accounts.all()
        return Response(SocialAccountSerializer(accounts, many=True).data)


class SocialAccountUnlinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = request.data.get('provider')
        if not provider:
            return Response({'detail': 'Provider is required.'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = request.user.social_accounts.filter(provider=provider).delete()
        if deleted:
            log_security_event(
                user=request.user,
                event_type='social_unlink',
                severity='info',
                description=f'Social account unlinked: {provider}',
            )
            return Response({'detail': f'{provider} account unlinked.'})
        return Response({'detail': f'No {provider} account linked.'}, status=status.HTTP_404_NOT_FOUND)


# Security Events
class SecurityEventListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        events = request.user.security_events.all()[:50]
        return Response(SecurityEventSerializer(events, many=True).data)


# Activity Log
class ActivityLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = request.user.activity_logs.all()[:50]
        return Response(ActivityLogSerializer(logs, many=True).data)


# Terms & Consent
class TermsVersionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Q
        terms = TermsVersion.objects.filter(is_active=True).order_by('-effective_date').first()
        if not terms:
            return Response({'version': '1.0', 'content': 'Terms of Service', 'is_active': True})
        return Response(TermsVersionSerializer(terms).data)


class TermsAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TermsAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = serializer.validated_data['version']
        marketing_consent = serializer.validated_data.get('marketing_consent', False)

        user = request.user
        user.accept_terms(version)
        if marketing_consent:
            user.set_marketing_consent(True)
        else:
            user.set_marketing_consent(False)

        log_security_event(
            user=user,
            event_type='terms_accepted',
            severity='info',
            description=f'Terms version {version} accepted',
        )

        return Response({'detail': 'Terms accepted successfully.'})


class PrivacyAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.accept_privacy()
        log_security_event(
            user=user,
            event_type='privacy_accepted',
            severity='info',
            description='Privacy policy accepted',
        )
        return Response({'detail': 'Privacy policy accepted successfully.'})


# Data Export
class DataExportRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        exports = request.user.data_export_requests.all().order_by('-requested_at')[:10]
        return Response(DataExportRequestSerializer(exports, many=True).data)

    def post(self, request):
        serializer = DataExportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        export = DataExportRequest.objects.create(user=user, status='pending')

        # Generate export data
        export_data = self._generate_user_data(user)
        filename = f"learnwise_data_export_{user.id}_{uuid.uuid4().hex}.json"
        # Stored outside MEDIA_ROOT so it is never served publicly; download goes through an authenticated view
        filepath = settings.BASE_DIR / 'private' / 'exports' / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        export.file_path = str(filepath)
        export.file_size = filepath.stat().st_size
        export.status = 'completed'
        export.completed_at = timezone.now()
        export.expires_at = timezone.now() + timezone.timedelta(days=7)
        export.save()

        log_security_event(
            user=user,
            event_type='data_export_requested',
            severity='info',
            description=f'Personal data exported: {filename}',
        )

        return Response(DataExportRequestSerializer(export).data, status=status.HTTP_201_CREATED)

    def _generate_user_data(self, user):
        data = {
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'bio': user.bio,
                'phone': user.phone,
                'email_verified': user.email_verified,
            },
            'sessions': list(user.sessions.values('session_key', 'ip_address', 'device_info', 'created_at', 'last_activity', 'revoked_at')),
            'security_events': list(user.security_events.values('event_type', 'severity', 'description', 'ip_address', 'created_at')),
            'activity_logs': list(user.activity_logs.values('action', 'resource_type', 'resource_id', 'description', 'created_at')),
            'social_accounts': list(user.social_accounts.values('provider', 'provider_user_id', 'created_at')),
        }
        return data


# Data export download (authenticated, owner only)
class DataExportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, export_id):
        export = request.user.data_export_requests.filter(id=export_id, status='completed').first()
        if not export or not export.file_path:
            return Response({'detail': 'Export not found.'}, status=status.HTTP_404_NOT_FOUND)
        if export.expires_at and export.expires_at < timezone.now():
            return Response({'detail': 'This export has expired.'}, status=status.HTTP_410_GONE)

        exports_dir = (settings.BASE_DIR / 'private' / 'exports').resolve()
        path = Path(export.file_path).resolve()
        if exports_dir not in path.parents or not path.is_file():
            return Response({'detail': 'Export file not available.'}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(open(path, 'rb'), as_attachment=True, filename=path.name, content_type='application/json')


# Account Deletion
class AccountDeletionRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            deletion = request.user.deletion_request
        except AccountDeletionRequest.DoesNotExist:
            return Response({})
        return Response({
            'id': deletion.id,
            'status': deletion.status,
            'reason': deletion.reason,
            'feedback': deletion.feedback,
            'requested_at': deletion.requested_at,
            'confirmed_at': deletion.confirmed_at,
            'scheduled_deletion_at': deletion.scheduled_deletion_at,
            'completed_at': deletion.completed_at,
            'cancelled_at': deletion.cancelled_at,
        })

    def post(self, request):
        step_up = require_step_up(request)
        if step_up:
            return step_up
        serializer = AccountDeletionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        existing = AccountDeletionRequest.objects.filter(user=user).first()
        if existing and existing.status in ('confirmed', 'processing'):
            return Response({'detail': 'An account deletion is already scheduled.'}, status=status.HTTP_400_BAD_REQUEST)

        # One request per user (OneToOne): reuse the row with a fresh confirmation token
        deletion, _ = AccountDeletionRequest.objects.update_or_create(
            user=user,
            defaults={
                'status': 'pending',
                'reason': serializer.validated_data.get('reason', ''),
                'feedback': serializer.validated_data.get('feedback', ''),
                'confirmation_token': uuid.uuid4(),
                'confirmed_at': None,
                'scheduled_deletion_at': None,
                'cancelled_at': None,
                'completed_at': None,
            },
        )
        self._send_confirmation_email(user, deletion)

        log_security_event(
            user=user,
            event_type='account_deletion_requested',
            severity='critical',
            description='Account deletion requested',
        )

        return Response({
            'detail': 'Account deletion request submitted. A confirmation email has been sent.',
            'deletion_id': deletion.id,
        }, status=status.HTTP_201_CREATED)

    def _send_confirmation_email(self, user, deletion):
        subject = 'Confirm your Learnwise account deletion'
        message = f'''Hello {user.first_name or user.email},

We received a request to delete your Learnwise account.

To confirm, enter this confirmation code together with your password in the app:
{deletion.confirmation_token}

After confirmation your account is permanently deleted after 30 days. You can cancel at any time before then.

If you didn't request this, ignore this email and change your password.

Best regards,
The Learnwise Team'''

        try:
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            else:
                logger.info(f"[DEV EMAIL] To: {user.email}, Subject: {subject}, Message: {message}")
        except Exception as e:
            logger.error(f"Failed to send deletion confirmation email to {user.email}: {e}")


class AccountDeletionConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AccountDeletionConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        user = request.user

        # Only check password if user has a usable password (not OAuth-only)
        if user.has_usable_password() and password:
            if not user.check_password(password):
                return Response({'detail': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        elif user.has_usable_password() and not password:
            return Response({'detail': 'Password is required to confirm account deletion.'}, status=status.HTTP_400_BAD_REQUEST)
        # For OAuth-only users (no usable password), skip password check

        try:
            deletion = AccountDeletionRequest.objects.get(
                user=user,
                confirmation_token=token,
                status='pending'
            )
        except AccountDeletionRequest.DoesNotExist:
            return Response({'detail': 'Invalid confirmation token.'}, status=status.HTTP_400_BAD_REQUEST)

        deletion.status = 'confirmed'
        deletion.confirmed_at = timezone.now()
        deletion.scheduled_deletion_at = timezone.now() + timezone.timedelta(days=30)
        deletion.save()

        log_security_event(
            user=user,
            event_type='account_deletion_requested',
            severity='critical',
            description='Account deletion confirmed. Scheduled for deletion in 30 days.',
        )

        return Response({'detail': 'Account deletion confirmed. Your account will be permanently deleted in 30 days.'})


class CancelDeletionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            deletion = user.deletion_request
        except AccountDeletionRequest.DoesNotExist:
            return Response({'detail': 'No pending account deletion request found.'}, status=status.HTTP_404_NOT_FOUND)

        if deletion.status in ['pending', 'confirmed']:
            deletion.status = 'cancelled'
            deletion.cancelled_at = timezone.now()
            deletion.save()

            log_security_event(
                user=user,
                event_type='profile_updated',
                severity='info',
                description='Account deletion cancelled by user',
            )

            return Response({'detail': 'Account deletion request has been cancelled.'})
        else:
            return Response({'detail': 'Cannot cancel this deletion request.'}, status=status.HTTP_400_BAD_REQUEST)


# Admin User Management
class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'username', 'first_name', 'last_name']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AdminUserUpdateSerializer
        if self.action == 'create':
            return AdminUserCreateSerializer
        return AdminUserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        # Admins can't see other admins unless they are superuser
        user = self.request.user
        if user.is_superuser:
            return User.objects.all().order_by('-date_joined')
        return User.objects.exclude(role='admin').exclude(is_superuser=True).order_by('-date_joined')

    def get_object(self):
        obj = super().get_object()
        # Prevent non-superusers from accessing admin / superuser accounts
        if not self.request.user.is_superuser and (obj.role == 'admin' or obj.is_superuser):
            self.permission_denied(self.request, message='Cannot access admin users.')
        return obj

    def perform_destroy(self, instance):
        actor = self.request.user
        if instance.pk == actor.pk:
            raise PermissionDenied('You cannot delete your own account.')
        if instance.is_superuser and not actor.is_superuser:
            raise PermissionDenied('Only superusers can delete superuser accounts.')
        email = instance.email
        instance.delete()
        log_security_event(
            user=actor,
            event_type='admin_delete',
            severity='critical',
            description=f'Account {email} deleted by admin {actor.email}',
        )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'Cannot modify your own status.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save(update_fields=['is_active'])
        log_security_event(
            user=user,
            event_type='admin_activate',
            severity='info',
            description=f'Account activated by admin {request.user.email}',
        )
        return Response({'detail': 'User activated.'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'Cannot deactivate yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=['is_active'])
        # Kick the user out immediately instead of waiting for the access token to expire
        revoke_user_sessions(user, blacklist_tokens=True)
        log_security_event(
            user=user,
            event_type='admin_deactivate',
            severity='warning',
            description=f'Account deactivated by admin {request.user.email}',
        )
        return Response({'detail': 'User deactivated.'})

    @action(detail=True, methods=['post'])
    def make_admin(self, request, pk=None):
        user = self.get_object()
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can promote users to admin.'}, status=status.HTTP_403_FORBIDDEN)
        if user.role == 'admin':
            return Response({'detail': 'User is already an admin.'}, status=status.HTTP_400_BAD_REQUEST)
        previous_role = user.role
        user.role = 'admin'
        user.is_staff = True
        user.save(update_fields=['role', 'is_staff'])
        log_security_event(
            user=user,
            event_type='admin_promote',
            severity='warning',
            description=f'Promoted from {previous_role} to admin by {request.user.email}',
        )
        return Response({'detail': 'User promoted to admin.'})

    @action(detail=True, methods=['post'])
    def remove_admin(self, request, pk=None):
        user = self.get_object()
        if not request.user.is_superuser:
            return Response({'detail': 'Only superusers can remove admin privileges.'}, status=status.HTTP_403_FORBIDDEN)
        if user == request.user:
            return Response({'detail': 'Cannot remove admin from yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_superuser:
            # Restore to previous role if it was professor, otherwise etudiant
            user.role = 'professeur' if user.role == 'professeur' else 'etudiant'
        else:
            user.role = 'etudiant'
            user.is_superuser = False
        user.is_staff = False
        user.save(update_fields=['role', 'is_staff', 'is_superuser'])
        log_security_event(
            user=user,
            event_type='admin_demote',
            severity='warning',
            description=f'Admin privileges removed by {request.user.email}',
        )
        return Response({'detail': 'Admin privileges removed.'})

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'Cannot lock your own account.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser and not request.user.is_superuser:
            return Response({'detail': 'Cannot lock superuser account.'}, status=status.HTTP_403_FORBIDDEN)
        user.locked_until = timezone.now() + timezone.timedelta(days=365)
        user.save(update_fields=['locked_until'])
        revoke_user_sessions(user, blacklist_tokens=True)
        log_security_event(
            user=user,
            event_type='admin_lock',
            severity='warning',
            description=f'Account locked by admin {request.user.email}',
        )
        return Response({'detail': 'User account locked.'})

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'Cannot unlock your own account.'}, status=status.HTTP_400_BAD_REQUEST)
        user.locked_until = None
        user.failed_login_attempts = 0
        user.save(update_fields=['locked_until', 'failed_login_attempts'])
        log_security_event(
            user=user,
            event_type='admin_unlock',
            severity='info',
            description=f'Account unlocked by admin {request.user.email}',
        )
        return Response({'detail': 'User account unlocked.'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = User.objects.count()
        students = User.objects.filter(role='etudiant').count()
        teachers = User.objects.filter(role='professeur').count()
        admins = User.objects.filter(role='admin').count()
        active = User.objects.filter(is_active=True).count()
        verified = User.objects.filter(email_verified=True).count()
        two_fa = User.objects.filter(two_factor_enabled=True).count()
        locked = User.objects.filter(locked_until__isnull=False).count()
        return Response({
            'total': total,
            'students': students,
            'teachers': teachers,
            'admins': admins,
            'active': active,
            'verified': verified,
            'two_factor_enabled': two_fa,
            'locked_accounts': locked,
        })


class StepUpView(APIView):
    """Step-up re-authentication: elevate a face-authenticated session to password auth.
    
    This endpoint allows a face-authenticated session (weaker, no liveness check)
    to be upgraded to password authentication by verifying the user's password.
    It returns new tokens with auth_method='password' WITHOUT creating a new session,
    so the existing session is elevated rather than duplicated.
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'step_up'

    def post(self, request):
        serializer = StepUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']

        user = request.user

        if not user.check_password(password):
            return Response({'detail': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate new tokens with auth_method='password' and a fresh session id
        # so the elevated session can be revoked independently.
        tokens = get_tokens_for_user(user, request, auth_method='password')

        log_security_event(
            user=user,
            event_type='step_up',
            severity='info',
            description='Session elevated from face to password authentication',
        )

        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        })


class StepUpSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)