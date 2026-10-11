import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import EmailVerification, PasswordResetToken, SocialAccount
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SocialAuthSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.check_password(password):
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'detail': 'This account is deactivated.'},
                status=status.HTTP_403_FORBIDDEN
            )

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        return Response({'detail': 'Successfully logged out.'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
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

        return Response({'detail': 'If an account exists for that email, a reset link will be sent.'})

    def _send_reset_email(self, user, reset_link):
        subject = 'Reset your Learnwise password'
        message = f'''
Hello {user.first_name or user.email},

You requested a password reset for your Learnwise account.

Click the link below to set a new password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
The Learnwise Team
        '''.strip()

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
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
            return Response(
                {'detail': 'Invalid or expired reset token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reset_token.is_valid():
            return Response(
                {'detail': 'This reset link has expired or has already been used.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reset_token.user.set_password(password)
        reset_token.user.save()
        reset_token.mark_used()

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
            return Response(
                {'detail': 'Invalid verification token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not verification.is_valid():
            return Response(
                {'detail': 'This verification link has expired.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification.mark_verified()
        tokens = get_tokens_for_user(verification.user)

        return Response({
            'detail': 'Email verified successfully.',
            'user': UserSerializer(verification.user).data,
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
            verification.token = verification.__class__.objects.model._meta.get_field('token').default
            verification.created_at = timezone.now()
            verification.verified_at = None
            verification.save()

        self._send_verification_email(user, verification)

        return Response({'detail': 'Verification email sent.'})

    def _send_verification_email(self, user, verification):
        verification_link = f"{settings.FRONTEND_URL}/auth/verify?token={verification.token}"
        subject = 'Verify your Learnwise email address'
        message = f'''
Hello {user.first_name or user.email},

Welcome to Learnwise! Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
The Learnwise Team
        '''.strip()

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
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

        # If code is provided, exchange it for access token
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
            'user': UserSerializer(user).data,
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

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = User.objects.count()
        students = User.objects.filter(role='etudiant').count()
        teachers = User.objects.filter(role='professeur').count()
        admins = User.objects.filter(role='admin').count()
        active = User.objects.filter(is_active=True).count()
        verified = User.objects.filter(email_verified=True).count()
        return Response({
            'total': total,
            'students': students,
            'teachers': teachers,
            'admins': admins,
            'active': active,
            'verified': verified,
        })