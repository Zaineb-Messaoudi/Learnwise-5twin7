import qrcode
import io
import base64
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import (
    EmailVerification,
    UserSession,
    SecurityEvent,
    ActivityLog,
    DataExportRequest,
    AccountDeletionRequest,
    TermsVersion,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    two_factor_enabled = serializers.BooleanField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)
    terms_accepted = serializers.BooleanField(read_only=True)
    privacy_accepted = serializers.BooleanField(read_only=True)
    marketing_consent = serializers.BooleanField(read_only=True)
    locked = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'name',
            'role', 'is_active', 'date_joined', 'avatar', 'avatar_url',
            'phone', 'bio', 'email_verified', 'two_factor_enabled',
            'terms_accepted', 'privacy_accepted', 'marketing_consent',
            'locked', 'pending_email',
        ]
        read_only_fields = ['id', 'date_joined', 'is_active', 'email_verified', 'two_factor_enabled', 'locked', 'pending_email']

    def get_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name or obj.email

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_locked(self, obj):
        return obj.is_locked()

    def get_terms_accepted(self, obj):
        return obj.terms_accepted_at is not None

    def get_privacy_accepted(self, obj):
        return obj.privacy_accepted_at is not None


class UserProfileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'name',
            'avatar', 'avatar_url', 'phone', 'bio', 'email_verified',
            'terms_accepted', 'privacy_accepted', 'marketing_consent',
        ]
        read_only_fields = ['id', 'email', 'email_verified']

    def get_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name or obj.email

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='etudiant')
    terms_version = serializers.CharField(required=False)
    marketing_consent = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'confirm_password', 'role', 'terms_version', 'marketing_consent']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def create(self, validated_data):
        terms_version = validated_data.pop('terms_version', None)
        marketing_consent = validated_data.pop('marketing_consent', False)
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        user.is_active = True
        if terms_version:
            user.accept_terms(terms_version)
        if marketing_consent:
            user.set_marketing_consent(True)
        user.save()
        EmailVerification.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    totp_token = serializers.CharField(required=False, max_length=6)
    backup_code = serializers.CharField(required=False, max_length=8)
    remember_me = serializers.BooleanField(required=False, default=False)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if user.check_password_history(attrs['new_password']):
            raise serializers.ValidationError({'new_password': 'This password was recently used. Please choose a different one.'})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value, is_active=True).exists():
            raise serializers.ValidationError('If an account exists for that email, a reset link will be sent.')
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField()


class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'facebook'])
    access_token = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='etudiant')

    def validate(self, attrs):
        if not attrs.get('access_token') and not attrs.get('code'):
            raise serializers.ValidationError('Either access_token or code is required.')
        return attrs


class TwoFactorSetupSerializer(serializers.Serializer):
    secret = serializers.CharField(read_only=True)
    qr_code = serializers.CharField(read_only=True)
    backup_codes = serializers.ListField(child=serializers.CharField(), read_only=True)


class TwoFactorVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=6)
    backup_code = serializers.CharField(max_length=8, required=False)


class TwoFactorDisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    token = serializers.CharField(max_length=6, required=False)
    backup_code = serializers.CharField(max_length=8, required=False)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['password']):
            raise serializers.ValidationError({'password': 'Current password is incorrect.'})
        if not attrs.get('token') and not attrs.get('backup_code'):
            raise serializers.ValidationError('Either TOTP token or backup code is required.')
        return attrs


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField()

    def validate_new_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()


class EmailChangeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.BooleanField(read_only=True)
    device_name = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = ['id', 'session_key', 'ip_address', 'device_info', 'device_name', 'location', 'created_at', 'last_activity', 'is_current', 'revoked_at']
        read_only_fields = fields

    def get_device_name(self, obj):
        device = obj.device_info or {}
        browser = device.get('browser', 'Unknown')
        os = device.get('os', 'Unknown')
        device_type = device.get('device_type', 'desktop')
        return f"{browser} on {os} ({device_type})"


class SecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityEvent
        fields = ['id', 'event_type', 'severity', 'description', 'ip_address', 'metadata', 'created_at']
        read_only_fields = fields


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ['id', 'action', 'resource_type', 'resource_id', 'description', 'ip_address', 'metadata', 'created_at']
        read_only_fields = fields


class DataExportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExportRequest
        fields = ['id', 'status', 'file_path', 'file_size', 'requested_at', 'completed_at', 'expires_at', 'error_message']
        read_only_fields = fields


class DataExportCreateSerializer(serializers.Serializer):
    pass


class AccountDeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountDeletionRequest
        fields = ['id', 'status', 'reason', 'feedback', 'requested_at', 'confirmed_at', 'scheduled_deletion_at', 'completed_at', 'cancelled_at']
        read_only_fields = fields


class AccountDeletionCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    feedback = serializers.CharField(required=False, allow_blank=True)


class AccountDeletionConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TermsVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsVersion
        fields = ['version', 'title', 'content', 'effective_date', 'is_active']
        read_only_fields = fields


class TermsAcceptSerializer(serializers.Serializer):
    version = serializers.CharField()
    marketing_consent = serializers.BooleanField(required=False, default=False)


class AdminUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    last_login_display = serializers.SerializerMethodField()
    email_verified = serializers.BooleanField(read_only=True)
    two_factor_enabled = serializers.BooleanField(read_only=True)
    locked = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'name', 'role', 'is_active', 'is_staff', 'email_verified', 'two_factor_enabled', 'locked', 'date_joined', 'last_login_display']
        read_only_fields = ['id', 'date_joined', 'last_login_display', 'email_verified', 'two_factor_enabled', 'locked']

    def get_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name or obj.email

    def get_last_login_display(self, obj):
        return obj.last_login.isoformat() if obj.last_login else None

    def get_locked(self, obj):
        return obj.is_locked()


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'is_staff']

    def validate_email(self, value):
        user = self.instance
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate_username(self, value):
        user = self.instance
        if User.objects.filter(username__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField()

    def validate_avatar(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Avatar must be less than 5MB.')
        return value