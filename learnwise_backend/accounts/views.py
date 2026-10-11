import io
import json
import base64
import hashlib
import logging
import qrcode
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.http import FileResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, permissions, generics
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

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
)
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    DataExportCreateSerializer,
    DataExportRequestSerializer,
    EmailChangeConfirmSerializer,
    EmailChangeRequestSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SocialAuthSerializer,
    TermsAcceptSerializer,
    TermsVersionSerializer,
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


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


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

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

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

        if user.is_locked():
            return Response(
                {'detail': 'Your account has been temporarily locked due to multiple failed login attempts. Please try again later.'},
                status=status.HTTP_403_FORBIDDEN
            )

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

        if not user.is_active:
            return Response({'detail': 'This account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)

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

        # Create session record
        session_key = request.META.get('HTTP_AUTHORIZATION', '').split(' ')[-1]
        if session_key:
            device_info = parse_user_agent(user_agent)
            UserSession.objects.create(
                user=user,
                session_key=hashlib.sha256(session_key.encode()).hexdigest()[:40],
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info,
                is_current=True,
            )

        tokens = get_tokens_for_user(user)
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

        # Mark sessions as not current
        request.user.sessions.update(is_current=False)

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

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()

        user = User.objects.get(email__iexact=email)
        reset_token = PasswordResetToken.objects.create(user=user)

        reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token.token}"
        self._send_reset_email(user, reset_link)

        log_security_event(
            user=user,
            event_type='password_change',
            severity='info',
            description='Password reset requested',
        )

        return Response({'detail': 'If an account exists for that email, a reset link will be sent.'})


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
        except PasswordResetToken.DoesNotExist:
            return Response({'detail': 'Invalid or expired reset token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not reset_token.is_valid():
            return Response({'detail': 'This reset link has expired or has already been used.'}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user

        # Check password history
        if user.check_password_history(password):
            return Response({'detail': 'This password was recently used. Please choose a different one.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()
        old_hash = user.password
        user.add_password_to_history(old_hash)
        reset_token.mark_used()

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
        except EmailVerification.DoesNotExist:
            return Response({'detail': 'Invalid verification token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not verification.is_valid():
            return Response({'detail': 'This verification link has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        verification.mark_verified()
        tokens = get_tokens_for_user(verification.user)

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
            verification.save()

        self._send_verification_email(user, verification)

        return Response({'detail': 'Verification email sent.'})

    def _send_verification_email(self, user, verification):
        verification_link = f"{settings.FRONTEND_URL}/auth/verify?token={verification.token}"
        subject = 'Verify your Learnwise email address'
        message = f'''Hello {user.first_name or user.email},

Welcome to Learnwise! Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
The Learnwise Team'''

        try:
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            else:
                logger.info(f"[DEV EMAIL] To: {user.email}, Subject: {subject}, Message: {message}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")


class SocialAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data.get('access_token')
        code = serializer.validated_data.get('code')
        role = serializer.validated_data.get('role', 'etudiant')

        if code and not access_token:
            if provider == 'google':
                access_token = self._exchange_google_code(code)
            elif provider == 'facebook':
                access_token = self._exchange_facebook_code(code)
            else:
                return Response({'detail': 'Unsupported provider.'}, status=status.HTTP_400_BAD_REQUEST)

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

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': user_data.get('given_name', user_data.get('first_name', '')),
                'last_name': user_data.get('family_name', user_data.get('last_name', '')),
                'role': role,
                'email_verified': True,
            }
        )

        if created:
            user.set_unusable_password()
            user.save()
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
            log_security_event(
                user=user,
                event_type='login',
                severity='info',
                description=f'Login via {provider} OAuth',
            )

        SocialAccount.objects.update_or_create(
            user=user,
            provider=provider,
            defaults={
                'provider_user_id': user_data.get('sub', user_data.get('id')),
                'access_token': access_token,
            }
        )

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'is_new_user': created,
        })

    def _exchange_google_code(self, code):
        import requests
        try:
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': settings.GOOGLE_CALLBACK_URL,
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('access_token')
        except Exception as e:
            logger.error(f"Google code exchange failed: {e}")
        return None

    def _exchange_facebook_code(self, code):
        import requests
        try:
            response = requests.get(
                'https://graph.facebook.com/v23.0/oauth/access_token',
                params={
                    'client_id': settings.FACEBOOK_APP_ID,
                    'client_secret': settings.FACEBOOK_APP_SECRET,
                    'code': code,
                    'redirect_uri': settings.FACEBOOK_CALLBACK_URL,
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('access_token')
        except Exception as e:
            logger.error(f"Facebook code exchange failed: {e}")
        return None

    def _verify_google_token(self, access_token):
        import requests
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Google token verification failed: {e}")
        return None

    def _verify_facebook_token(self, access_token):
        import requests
        try:
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


# Two-Factor Authentication Views
class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.totp_secret:
            user.generate_totp_secret()
            user.refresh_from_db()

        backup_codes = list(user.backup_codes) if user.backup_codes else []

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

        verified = False
        if token and user.verify_totp(token):
            verified = True
        elif backup_code and user.use_backup_code(backup_code):
            verified = True

        if not verified:
            raise serializers.ValidationError({'token': 'Invalid TOTP token.'})

        # Generate backup codes if not exists
        if not user.backup_codes:
            user.generate_backup_codes(10)
            user.refresh_from_db()

        user.two_factor_enabled = True
        user.save(update_fields=['two_factor_enabled'])

        log_security_event(
            user=user,
            event_type='2fa_enabled',
            severity='info',
            description='Two-factor authentication enabled',
        )

        backup_codes = list(user.backup_codes)
        return Response({
            'detail': 'Two-factor authentication enabled successfully.',
            'backup_codes': backup_codes,
        })


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        user = request.user
        if user.email_change_token and str(user.email_change_token) == token:
            old_email = user.email
            if user.confirm_email_change(token):
                log_security_event(
                    user=user,
                    event_type='email_changed',
                    severity='info',
                    description=f'Email changed from {old_email} to {user.email}',
                )
                return Response({'detail': 'Email changed successfully. You will need to sign in again.'})
            else:
                return Response({'detail': 'Invalid or expired email change token.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


# Session Management Views
class UserSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = request.user.sessions.filter(revoked_at__isnull=True).order_by('-last_activity')
        return Response(UserSessionSerializer(sessions, many=True).data)


class RevokeSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = request.user.sessions.get(id=session_id, revoked_at__isnull=True)
        except UserSession.DoesNotExist:
            return Response({'detail': 'Session not found or already revoked.'}, status=status.HTTP_404_NOT_FOUND)

        session.revoke()
        log_security_event(
            user=request.user,
            event_type='session_revoked',
            severity='info',
            description=f'Session revoked: {session.device_name}',
        )
        return Response({'detail': 'Session revoked successfully.'})


class RevokeAllSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = request.user.sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
        log_security_event(
            user=request.user,
            event_type='all_sessions_revoked',
            severity='warning',
            description=f'All sessions revoked ({count} sessions)',
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
        filename = f"learnwise_data_export_{user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = settings.BASE_DIR / 'media' / 'exports' / filename
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
        serializer = AccountDeletionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        deletion = AccountDeletionRequest.objects.create(
            user=user,
            status='pending',
            reason=serializer.validated_data.get('reason', ''),
            feedback=serializer.validated_data.get('feedback', ''),
        )

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


class AccountDeletionConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AccountDeletionConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        user = request.user

        if not user.check_password(password):
            return Response({'detail': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

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
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    filterset_fields = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'username', 'first_name', 'last_name']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': 'User activated.'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'Cannot deactivate yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'detail': 'User deactivated.'})

    @action(detail=True, methods=['post'])
    def make_admin(self, request, pk=None):
        user = self.get_object()
        user.role = 'admin'
        user.is_staff = True
        user.save(update_fields=['role', 'is_staff'])
        return Response({'detail': 'User promoted to admin.'})

    @action(detail=True, methods=['post'])
    def remove_admin(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'Cannot remove admin from yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = 'etudiant'
        user.is_staff = False
        user.save(update_fields=['role', 'is_staff'])
        return Response({'detail': 'Admin privileges removed.'})

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'Cannot lock your own account.'}, status=status.HTTP_400_BAD_REQUEST)
        user.locked_until = timezone.now() + timezone.timedelta(days=365)
        user.save(update_fields=['locked_until'])
        return Response({'detail': 'User account locked.'})

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        user = self.get_object()
        user.locked_until = None
        user.failed_login_attempts = 0
        user.save(update_fields=['locked_until', 'failed_login_attempts'])
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