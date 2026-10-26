import re
import qrcode
import io
import base64
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from .models import (
    EmailVerification,
    UserSession,
    SecurityEvent,
    ActivityLog,
    DataExportRequest,
    AccountDeletionRequest,
    TermsVersion,
    FaceProfile,
)

User = get_user_model()

# Backup codes are shown as XXXXX-XXXXX (10 characters + a dash); leave room for spaces
# so a pasted code is never rejected before it reaches the verification logic.
BACKUP_CODE_MAX_LENGTH = 32

class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    two_factor_enabled = serializers.BooleanField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)
    terms_accepted = serializers.SerializerMethodField()
    privacy_accepted = serializers.SerializerMethodField()
    marketing_consent = serializers.BooleanField(read_only=True)
    locked = serializers.SerializerMethodField()
    needs_role_selection = serializers.SerializerMethodField()
    needs_face_profile = serializers.SerializerMethodField()
    needs_onboarding = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'name',
            'role', 'is_active', 'date_joined', 'avatar', 'avatar_url',
            'phone', 'bio', 'email_verified', 'two_factor_enabled',
            'terms_accepted', 'privacy_accepted', 'marketing_consent',
            'locked', 'pending_email',
            'needs_role_selection', 'needs_face_profile', 'needs_onboarding',
            'has_password', 'is_superuser',
        ]
        read_only_fields = ['id', 'date_joined', 'is_active', 'email_verified', 'two_factor_enabled', 'locked', 'pending_email', 'is_superuser']

    def get_has_password(self, obj):
        # False for accounts created through Google/Facebook (no local password)
        return obj.has_usable_password()

    def get_needs_role_selection(self, obj):
        return obj.needs_role_selection()

    def get_needs_face_profile(self, obj):
        return obj.needs_face_profile()

    def get_needs_onboarding(self, obj):
        return obj.needs_onboarding()

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
    terms_accepted = serializers.SerializerMethodField()
    privacy_accepted = serializers.SerializerMethodField()
    marketing_consent = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'name',
            'avatar', 'avatar_url', 'phone', 'bio', 'email_verified',
            'terms_accepted', 'privacy_accepted', 'marketing_consent',
        ]
        read_only_fields = ['id', 'email', 'email_verified']

    def validate_avatar(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Avatar must be less than 5MB.')
        return value

    def validate_phone(self, value):
        if value and not re.fullmatch(r'^\+?[0-9\s\-()]{7,20}$', value):
            raise serializers.ValidationError('Enter a valid phone number.')
        return value

    def validate_first_name(self, value):
        if value and not re.fullmatch(r'^[A-Za-zÀ-ÖØ-öø-ÿ\u00C0-\u00FF\s\'\-]{0,50}$', value):
            raise serializers.ValidationError('First name contains invalid characters.')
        return value

    def validate_last_name(self, value):
        if value and not re.fullmatch(r'^[A-Za-zÀ-ÖØ-öø-ÿ\u00C0-\u00FF\s\'\-]{0,50}$', value):
            raise serializers.ValidationError('Last name contains invalid characters.')
        return value

    def update(self, instance, validated_data):
        # Keep the consent timestamp in sync with the flag
        consent = validated_data.pop('marketing_consent', None)
        instance = super().update(instance, validated_data)
        if consent is not None and consent != instance.marketing_consent:
            instance.set_marketing_consent(consent)
        return instance

    def get_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name or obj.email

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_terms_accepted(self, obj):
        return obj.terms_accepted_at is not None

    def get_privacy_accepted(self, obj):
        return obj.privacy_accepted_at is not None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    # The sign-up form has no username field: one is derived from the email when omitted
    username = serializers.CharField(required=False, allow_blank=True)
    # Public registration roles - admin excluded
    PUBLIC_ROLE_CHOICES = [('etudiant', 'Étudiant'), ('professeur', 'Professeur')]
    role = serializers.ChoiceField(choices=PUBLIC_ROLE_CHOICES, default='etudiant')
    terms_version = serializers.CharField(required=False)
    marketing_consent = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'confirm_password', 'role', 'terms_version', 'marketing_consent']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        if not attrs.get('username'):
            import secrets
            base = (attrs.get('email', '').split('@')[0] or 'user')[:130]
            candidate = base
            while User.objects.filter(username__iexact=candidate).exists():
                candidate = f"{base}{secrets.token_hex(2)}"
            attrs['username'] = candidate
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate_first_name(self, value):
        if value and not re.fullmatch(r'^[A-Za-zÀ-ÖØ-öø-ÿ\u00C0-\u00FF\s\'\-]{0,50}$', value):
            raise serializers.ValidationError('First name contains invalid characters.')
        return value

    def validate_last_name(self, value):
        if value and not re.fullmatch(r'^[A-Za-zÀ-ÖØ-öø-ÿ\u00C0-\u00FF\s\'\-]{0,50}$', value):
            raise serializers.ValidationError('Last name contains invalid characters.')
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username__iexact=value).exists():
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
        verification = EmailVerification.objects.create(user=user)
        verification.generate_code()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    totp_token = serializers.CharField(required=False, max_length=6)
    backup_code = serializers.CharField(required=False, max_length=BACKUP_CODE_MAX_LENGTH)
    remember_me = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Email is required.')
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError('Enter a valid email address.')
        return value.strip().lower()

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError('Password is required.')
        return value

    def validate_totp_token(self, value):
        if value and not re.fullmatch(r'\d{6}', value):
            raise serializers.ValidationError('TOTP token must be exactly 6 digits.')
        return value


class ChangePasswordSerializer(serializers.Serializer):
    # Not required for accounts that signed up with Google/Facebook and have no password yet
    current_password = serializers.CharField(required=False, allow_blank=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        user = self.context['request'].user
        if user.has_usable_password():
            if not user.check_password(attrs.get('current_password', '')):
                raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if user.check_password_history(attrs['new_password']):
            raise serializers.ValidationError({'new_password': 'This password was recently used. Please choose a different one.'})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Do not reveal whether the account exists (prevents user enumeration);
        # the view silently does nothing for unknown addresses.
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

    def validate_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Token is required.')
        return value.strip()


class EmailVerifyCodeSerializer(serializers.Serializer):
    code = serializers.RegexField(
        regex=r'^\d{6}$',
        max_length=6,
        min_length=6,
        error_messages={
            'invalid': 'The verification code must be exactly 6 digits.',
            'max_length': 'The verification code must be exactly 6 digits.',
            'min_length': 'The verification code must be exactly 6 digits.',
            'required': 'The verification code is required.',
        },
    )

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('The verification code must contain only digits.')
        if len(value) != 6:
            raise serializers.ValidationError('The verification code must be exactly 6 digits.')
        return value


class SelectRoleSerializer(serializers.Serializer):
    """Used by the post-signup 'pick a role' onboarding step (mainly for
    social-auth accounts created without a role). Admin is deliberately not
    an option here — admin role can only be granted via the admin API."""
    PUBLIC_ROLE_CHOICES = [('etudiant', 'Étudiant'), ('professeur', 'Professeur')]
    role = serializers.ChoiceField(choices=PUBLIC_ROLE_CHOICES)

    def validate(self, attrs):
        user = self.context['request'].user
        if user.role is not None:
            raise serializers.ValidationError('Role has already been set for this account.')
        return attrs


class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'facebook'])
    access_token = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    # Public registration roles - admin excluded
    PUBLIC_ROLE_CHOICES = [('etudiant', 'Étudiant'), ('professeur', 'Professeur')]
    role = serializers.ChoiceField(choices=PUBLIC_ROLE_CHOICES, required=False, allow_null=True)
    # Needed to complete login for accounts that have 2FA enabled
    totp_token = serializers.CharField(required=False, max_length=6)
    backup_code = serializers.CharField(required=False, max_length=BACKUP_CODE_MAX_LENGTH)

    def validate(self, attrs):
        if not attrs.get('access_token') and not attrs.get('code'):
            raise serializers.ValidationError('Either access_token or code is required.')
        totp_token = attrs.get('totp_token')
        if totp_token and not re.fullmatch(r'\d{6}', totp_token):
            raise serializers.ValidationError({'totp_token': 'TOTP token must be exactly 6 digits.'})
        return attrs


class TwoFactorSetupSerializer(serializers.Serializer):
    secret = serializers.CharField(read_only=True)
    qr_code = serializers.CharField(read_only=True)
    backup_codes = serializers.ListField(child=serializers.CharField(), read_only=True)


class TwoFactorVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=6)
    backup_code = serializers.CharField(max_length=BACKUP_CODE_MAX_LENGTH, required=False)

    def validate_token(self, value):
        if value and not re.fullmatch(r'\d{6}', value):
            raise serializers.ValidationError('TOTP token must be exactly 6 digits.')
        return value


class TwoFactorDisableSerializer(serializers.Serializer):
    # Not required for accounts that signed up with Google/Facebook and never had a password
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    token = serializers.CharField(max_length=6, required=False)
    backup_code = serializers.CharField(max_length=BACKUP_CODE_MAX_LENGTH, required=False)

    def validate_token(self, value):
        if value and not re.fullmatch(r'\d{6}', value):
            raise serializers.ValidationError('TOTP token must be exactly 6 digits.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if user.has_usable_password() and not user.check_password(attrs.get('password', '')):
            raise serializers.ValidationError({'password': 'Current password is incorrect.'})
        if not attrs.get('token') and not attrs.get('backup_code'):
            raise serializers.ValidationError('Either TOTP token or backup code is required.')

        # Verify TOTP token or backup code
        if attrs.get('token'):
            if not user.verify_totp(attrs['token']):
                raise serializers.ValidationError({'token': 'Invalid TOTP token.'})
        elif attrs.get('backup_code'):
            if not user.use_backup_code(attrs['backup_code']):
                raise serializers.ValidationError({'backup_code': 'Invalid or already used backup code.'})

        return attrs


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField()

    def validate_new_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()


class EmailChangeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Token is required.')
        return value.strip()


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()
    device_name = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = ['id', 'session_key', 'ip_address', 'device_info', 'device_name', 'location', 'created_at', 'last_activity', 'is_current', 'revoked_at']
        read_only_fields = fields

    def get_is_current(self, obj):
        current_sid = self.context.get('current_sid')
        return bool(current_sid) and obj.session_key == current_sid

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
        fields = ['id', 'status', 'file_size', 'requested_at', 'completed_at', 'expires_at', 'error_message']
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
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Token is required.')
        return value.strip()


class TermsVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsVersion
        fields = ['version', 'title', 'content', 'effective_date', 'is_active']
        read_only_fields = fields


class TermsAcceptSerializer(serializers.Serializer):
    version = serializers.CharField()
    marketing_consent = serializers.BooleanField(required=False, default=False)

    def validate_version(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Terms version is required.')
        return value.strip()


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


class _PrivilegedFieldsGuardMixin:
    """Only superusers may grant admin/staff privileges, non-superusers may not
    touch superuser accounts, and nobody may change their own role, staff flag
    or active flag through the admin API."""

    def _guard_privileged_fields(self, attrs):
        request = self.context.get('request')
        actor = getattr(request, 'user', None)
        is_super = bool(actor and actor.is_superuser)

        if not is_super:
            if attrs.get('role') == 'admin' or attrs.get('is_staff'):
                raise serializers.ValidationError('Only superusers can grant admin privileges.')

        instance = getattr(self, 'instance', None)
        if instance is not None:
            if instance.is_superuser and not is_super:
                raise serializers.ValidationError('Only superusers can modify superuser accounts.')
            if actor is not None and instance.pk == actor.pk:
                for field in ('role', 'is_staff', 'is_active'):
                    if field in attrs and attrs[field] != getattr(instance, field):
                        raise serializers.ValidationError({field: 'You cannot change this field on your own account.'})
        return attrs


class AdminUserUpdateSerializer(_PrivilegedFieldsGuardMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'is_staff']

    def validate(self, attrs):
        return self._guard_privileged_fields(attrs)

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


class AdminUserCreateSerializer(_PrivilegedFieldsGuardMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'password', 'confirm_password']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return self._guard_privileged_fields(attrs)

    def validate_email(self, value):
        # Case-insensitive uniqueness: login looks accounts up with email__iexact, so two
        # addresses differing only by case would make that lookup blow up.
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        # An administrator vouches for the address, otherwise the new user could never log in
        # (login requires a verified email and the account has no verification link).
        user.email_verified = True
        user.save()
        return user


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField()

    def validate_avatar(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Avatar must be less than 5MB.')
        return value


class FaceRegistrationSerializer(serializers.Serializer):
    descriptor = serializers.ListField(
        child=serializers.FloatField(),
        min_length=128,
        max_length=128,
        help_text='128-dimensional face descriptor from face-api.js'
    )
    quality_score = serializers.FloatField(min_value=0.0, max_value=1.0, required=False, default=0.0)
    enrollment_image = serializers.ImageField(required=False)

    def validate_descriptor(self, value):
        import numpy as np
        arr = np.array(value)
        if arr.shape != (128,):
            raise serializers.ValidationError('Descriptor must be 128-dimensional.')
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            raise serializers.ValidationError('Descriptor contains invalid values.')
        return value


class FaceVerificationSerializer(serializers.Serializer):
    descriptor = serializers.ListField(
        child=serializers.FloatField(),
        min_length=128,
        max_length=128,
        help_text='128-dimensional face descriptor from face-api.js'
    )

    def validate_descriptor(self, value):
        import numpy as np
        arr = np.array(value)
        if arr.shape != (128,):
            raise serializers.ValidationError('Descriptor must be 128-dimensional.')
        return value


class FaceProfileSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = FaceProfile
        fields = ['id', 'quality_score', 'enrollment_image', 'is_verified', 'verified_at', 'created_at']
        read_only_fields = fields