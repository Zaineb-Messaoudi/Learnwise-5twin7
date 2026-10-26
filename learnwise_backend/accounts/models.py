import base64
import hashlib
import hmac
import secrets
import uuid
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings


MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 30
MAX_FAILED_FACE_ATTEMPTS = 5
FACE_LOCKOUT_MINUTES = 30


class UserManager(DjangoUserManager):
    """Superusers made with `createsuperuser` must be able to sign in to the Learnwise
    API right away: mark their email as verified and give them the admin role
    (otherwise the email-verification check would lock them out of everything)."""

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('role', 'admin')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('etudiant', 'Étudiant'),
        ('professeur', 'Professeur'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    # 2FA / TOTP
    two_factor_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=32, blank=True)
    backup_codes = models.JSONField(default=list, blank=True)

    # Account lockout
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # Password history
    password_history = models.JSONField(default=list, blank=True)

    # Face-login lockout (face auth is weaker than password + 2FA: no liveness,
    # so brute-force / descriptor-reuse attempts must be rate-limited the same way)
    failed_face_attempts = models.IntegerField(default=0)
    face_locked_until = models.DateTimeField(null=True, blank=True)

    # Terms & consent
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_version = models.CharField(max_length=20, blank=True)
    privacy_accepted_at = models.DateTimeField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    marketing_consent_at = models.DateTimeField(null=True, blank=True)

    # Email change
    pending_email = models.EmailField(blank=True, null=True)
    email_change_token = models.UUIDField(null=True, blank=True)
    email_change_requested_at = models.DateTimeField(null=True, blank=True)

    # Last password change
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def name(self):
        full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full_name or self.email

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.first_name or self.username

    # --- Onboarding state ---------------------------------------------------
    # A single source of truth for whether a (typically social-signup) account
    # still needs to go through the role-selection and face-capture steps.
    # Used by UserSerializer so every endpoint that returns the user object
    # (login, social auth, /me/) agrees on this, and the frontend can always
    # redirect back into onboarding — on first login AND on any later login
    # that happens before onboarding is finished.
    @property
    def is_admin_account(self):
        return bool(self.is_superuser or self.role == 'admin')

    def needs_role_selection(self):
        return self.role is None and not self.is_superuser

    def needs_face_profile(self):
        # Administrators authenticate with password + 2FA, never with a face.
        if self.is_admin_account:
            return False
        try:
            return not self.face_profile.is_verified
        except FaceProfile.DoesNotExist:
            return True

    def face_login_allowed(self):
        """Face sign-in is a convenience for students/professors only. It is never
        offered for admin/staff accounts (there is no liveness check)."""
        allowed_roles = getattr(settings, 'FACE_LOGIN_ROLES', ('etudiant', 'professeur'))
        return bool(
            getattr(settings, 'FACE_LOGIN_ENABLED', True)
            and not self.is_admin_account
            and not self.is_staff
            and self.role in allowed_roles
        )

    def needs_onboarding(self):
        return self.needs_role_selection() or self.needs_face_profile()

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def record_failed_login(self):
        now = timezone.now()
        if self.locked_until:
            if now < self.locked_until:
                # Already locked: never extend the lock, otherwise anyone who knows
                # an email address could keep that account locked forever.
                return
            # A previous lock has expired: start counting from zero again
            self.failed_login_attempts = 0
            self.locked_until = None
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= MAX_FAILED_LOGINS:
            self.locked_until = now + timezone.timedelta(minutes=LOCKOUT_MINUTES)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def record_successful_login(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.failed_face_attempts = 0
        self.face_locked_until = None
        self.last_login = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'locked_until', 'failed_face_attempts', 'face_locked_until', 'last_login'])

    def is_face_locked(self):
        if self.face_locked_until and timezone.now() < self.face_locked_until:
            return True
        return False

    def record_failed_face_login(self):
        now = timezone.now()
        if self.face_locked_until:
            if now < self.face_locked_until:
                return
            self.failed_face_attempts = 0
            self.face_locked_until = None
        self.failed_face_attempts += 1
        if self.failed_face_attempts >= MAX_FAILED_FACE_ATTEMPTS:
            self.face_locked_until = now + timezone.timedelta(minutes=FACE_LOCKOUT_MINUTES)
        self.save(update_fields=['failed_face_attempts', 'face_locked_until'])

    def record_successful_face_login(self):
        self.failed_face_attempts = 0
        self.face_locked_until = None
        self.last_login = timezone.now()
        self.save(update_fields=['failed_face_attempts', 'face_locked_until', 'last_login'])

    def add_password_to_history(self, password_hash):
        history = self.password_history or []
        history.insert(0, password_hash)
        self.password_history = history[:10]
        self.password_changed_at = timezone.now()
        self.save(update_fields=['password_history', 'password_changed_at'])

    def check_password_history(self, password):
        from django.contrib.auth.hashers import check_password
        # Also block re-using the current password
        if self.has_usable_password() and self.check_password(password):
            return True
        for old_hash in (self.password_history or []):
            if check_password(password, old_hash):
                return True
        return False

    def generate_totp_secret(self):
        import pyotp
        secret = pyotp.random_base32()
        self.totp_secret = secret
        self.save(update_fields=['totp_secret'])
        return secret

    def get_totp_uri(self):
        import pyotp
        if not self.totp_secret:
            return None
        totp = pyotp.TOTP(self.totp_secret)
        return totp.provisioning_uri(self.email, issuer_name='Learnwise')

    def verify_totp(self, token):
        import pyotp
        from django.core.cache import cache
        if not self.totp_secret or not token or not str(token).isdigit():
            return False
        totp = pyotp.TOTP(self.totp_secret)
        if not totp.verify(token, valid_window=1):
            return False
        # Replay protection: a TOTP code can only be used once
        replay_key = f'totp_used:{self.pk}:{token}'
        if cache.get(replay_key):
            return False
        cache.set(replay_key, True, 120)
        return True

    BACKUP_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no 0/O/1/I look-alikes
    BACKUP_CODE_LENGTH = 10

    @staticmethod
    def _normalize_backup_code(code):
        return ''.join(str(code).split()).replace('-', '').upper()

    @classmethod
    def _hash_backup_code(cls, code):
        """Keyed hash (HMAC with SECRET_KEY): a leaked database alone cannot be
        brute-forced offline."""
        digest = hmac.new(
            settings.SECRET_KEY.encode(),
            cls._normalize_backup_code(code).encode(),
            hashlib.sha256,
        ).hexdigest()
        return f'v2${digest}'

    @staticmethod
    def _legacy_backup_hash(code):
        # Hashes written by older versions (unsalted SHA-256 of the 8-hex-char code)
        return hashlib.sha256(str(code).strip().upper().encode()).hexdigest()

    def generate_backup_codes(self, count=10):
        """Generate new backup codes (50 bits each). Only keyed hashes are stored;
        the plaintext codes are returned once so they can be shown to the user."""
        raw = [
            ''.join(secrets.choice(self.BACKUP_CODE_ALPHABET) for _ in range(self.BACKUP_CODE_LENGTH))
            for _ in range(count)
        ]
        self.backup_codes = [self._hash_backup_code(c) for c in raw]
        self.save(update_fields=['backup_codes'])
        half = self.BACKUP_CODE_LENGTH // 2
        return [f'{c[:half]}-{c[half:]}' for c in raw]

    def use_backup_code(self, code):
        """Consume a backup code. The row is locked so one code cannot be used by
        two concurrent requests."""
        if not code or not self._normalize_backup_code(code):
            return False
        candidates = {self._hash_backup_code(code), self._legacy_backup_hash(code)}
        with transaction.atomic():
            fresh = type(self).objects.select_for_update().get(pk=self.pk)
            remaining = list(fresh.backup_codes or [])
            for stored in remaining:
                if any(hmac.compare_digest(str(stored), candidate) for candidate in candidates):
                    remaining.remove(stored)
                    fresh.backup_codes = remaining
                    fresh.save(update_fields=['backup_codes'])
                    self.backup_codes = remaining
                    return True
        return False

    def request_email_change(self, new_email):
        self.pending_email = new_email
        self.email_change_token = uuid.uuid4()
        self.email_change_requested_at = timezone.now()
        self.save(update_fields=['pending_email', 'email_change_token', 'email_change_requested_at'])

    def confirm_email_change(self, token):
        if self.email_change_token == token and self.pending_email:
            if self.email_change_requested_at:
                expiry = self.email_change_requested_at + timezone.timedelta(hours=24)
                if timezone.now() > expiry:
                    return False
            # Make sure nobody took the address in the meantime
            if type(self).objects.filter(email__iexact=self.pending_email).exclude(pk=self.pk).exists():
                return False
            self.email = self.pending_email
            self.pending_email = None
            self.email_change_token = None
            self.email_change_requested_at = None
            # The new address was just proven by clicking the emailed link. Resetting
            # this to False used to lock the user out (login needs a verified email).
            self.email_verified = True
            self.save(update_fields=['email', 'pending_email', 'email_change_token', 'email_change_requested_at', 'email_verified'])
            return True
        return False

    def accept_terms(self, version='1.0'):
        self.terms_accepted_at = timezone.now()
        self.terms_version = version
        self.save(update_fields=['terms_accepted_at', 'terms_version'])

    def accept_privacy(self):
        self.privacy_accepted_at = timezone.now()
        self.save(update_fields=['privacy_accepted_at'])

    def set_marketing_consent(self, consent):
        self.marketing_consent = consent
        self.marketing_consent_at = timezone.now() if consent else None
        self.save(update_fields=['marketing_consent', 'marketing_consent_at'])


class EmailVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_verification')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    code = models.CharField(max_length=6, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_email_verification'
        indexes = [
            models.Index(fields=['user'], name='email_verification_user_idx'),
            models.Index(fields=['created_at'], name='email_verification_created_idx'),
        ]

    def __str__(self):
        return f"Email verification for {self.user.email}"

    def generate_code(self):
        self.code = f"{secrets.randbelow(1000000):06d}"
        self.save(update_fields=['code'])
        return self.code

    def is_valid(self):
        if self.verified_at:
            return False
        expiry = self.created_at + timezone.timedelta(hours=24)
        return timezone.now() < expiry

    def mark_verified(self):
        self.verified_at = timezone.now()
        self.save(update_fields=['verified_at'])
        self.user.email_verified = True
        self.user.save(update_fields=['email_verified'])


class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_password_reset_token'
        indexes = [
            models.Index(fields=['user'], name='password_reset_user_idx'),
            models.Index(fields=['created_at'], name='password_reset_created_idx'),
            models.Index(fields=['used_at'], name='password_reset_used_idx'),
        ]

    def __str__(self):
        return f"Password reset for {self.user.email}"

    def is_valid(self):
        if self.used_at:
            return False
        expiry = self.created_at + timezone.timedelta(hours=1)
        return timezone.now() < expiry

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class SocialAccount(models.Model):
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_social_account'
        unique_together = ['provider', 'provider_user_id']
        indexes = [
            models.Index(fields=['user'], name='social_account_user_idx'),
            models.Index(fields=['provider'], name='social_account_provider_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.provider}"


class UserSession(models.Model):
    AUTH_METHOD_CHOICES = [
        ('password', 'Password'),
        ('face', 'Face recognition'),
        ('social', 'Social OAuth'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    auth_method = models.CharField(max_length=20, choices=AUTH_METHOD_CHOICES, default='password')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_current = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_user_session'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'revoked_at', 'is_current'], name='sess_user_rev_cur_idx'),
            models.Index(fields=['user', 'last_activity'], name='sess_user_activity_idx'),
            models.Index(fields=['revoked_at'], name='sess_revoked_idx'),
            models.Index(fields=['is_current'], name='sess_current_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.device_info.get('browser', 'Unknown')} - {self.created_at}"

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=['revoked_at'])


class SecurityEvent(models.Model):
    EVENT_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('login_failed', 'Failed Login'),
        ('password_change', 'Password Changed'),
        ('email_change_requested', 'Email Change Requested'),
        ('email_changed', 'Email Changed'),
        ('2fa_enabled', '2FA Enabled'),
        ('2fa_disabled', '2FA Disabled'),
        ('backup_codes_generated', 'Backup Codes Generated'),
        ('session_revoked', 'Session Revoked'),
        ('all_sessions_revoked', 'All Sessions Revoked'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('profile_updated', 'Profile Updated'),
        ('avatar_updated', 'Avatar Updated'),
        ('terms_accepted', 'Terms Accepted'),
        ('privacy_accepted', 'Privacy Accepted'),
        ('marketing_consent_changed', 'Marketing Consent Changed'),
        ('data_export_requested', 'Data Export Requested'),
        ('account_deletion_requested', 'Account Deletion Requested'),
        ('account_deleted', 'Account Deleted'),
        ('face_registered', 'Face Registered'),
        ('face_login_failed', 'Face Login Failed'),
        ('admin_activate', 'Admin Activated Account'),
        ('admin_deactivate', 'Admin Deactivated Account'),
        ('admin_promote', 'Admin Promoted User'),
        ('admin_demote', 'Admin Demoted User'),
        ('admin_lock', 'Admin Locked Account'),
        ('admin_unlock', 'Admin Unlocked Account'),
        ('admin_delete', 'Admin Deleted Account'),
    ]

    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='security_events')
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_security_event'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['event_type', 'created_at'], name='sec_evt_type_created_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_event_type_display()} - {self.created_at}"


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('view', 'View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('export', 'Export'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]

    RESOURCE_TYPES = [
        ('course', 'Course'),
        ('material', 'Material'),
        ('quiz', 'Quiz'),
        ('exercise', 'Exercise'),
        ('notebook', 'Notebook'),
        ('assistant', 'Assistant'),
        ('profile', 'Profile'),
        ('settings', 'Settings'),
        ('user', 'User'),
        ('admin', 'Admin'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    resource_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_activity_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['user', 'resource_type']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['resource_type', 'resource_id'], name='activity_resource_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.action} {self.resource_type} - {self.created_at}"


class DataExportRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='data_export_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'accounts_data_export_request'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['user'], name='data_export_user_idx'),
            models.Index(fields=['status'], name='data_export_status_idx'),
            models.Index(fields=['requested_at'], name='data_export_requested_idx'),
        ]

    def __str__(self):
        return f"Data export for {self.user.email} - {self.status}"


class AccountDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deletion_request')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    confirmation_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    scheduled_deletion_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_account_deletion_request'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['user'], name='account_deletion_user_idx'),
            models.Index(fields=['status'], name='account_deletion_status_idx'),
            models.Index(fields=['scheduled_deletion_at'], name='account_deletion_scheduled_idx'),
        ]

    def __str__(self):
        return f"Account deletion for {self.user.email} - {self.status}"


class TermsVersion(models.Model):
    version = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    effective_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_terms_version'
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['is_active'], name='terms_active_idx'),
            models.Index(fields=['effective_date'], name='terms_effective_idx'),
        ]
        ordering = ['-effective_date']

    def __str__(self):
        return f"Terms v{self.version}"


class FaceProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='face_profile')
    descriptor = models.JSONField()
    quality_score = models.FloatField(default=0.0)
    enrollment_image = models.ImageField(upload_to='face_enrollment/', null=True, blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_face_profile'
        indexes = [
            models.Index(fields=['is_verified'], name='face_verified_idx'),
            models.Index(fields=['user', 'is_verified'], name='face_user_verified_idx'),
        ]

    def __str__(self):
        return f"Face profile for {self.user.email}"

    def verify_face(self, live_descriptor, threshold=None):
        import numpy as np
        if threshold is None:
            threshold = getattr(settings, 'FACE_MATCH_THRESHOLD', 0.5)
        try:
            stored = np.array(self.descriptor, dtype=float)
            live = np.array(live_descriptor, dtype=float)
        except (TypeError, ValueError):
            return False, float('inf')
        if stored.shape != live.shape or not np.all(np.isfinite(live)):
            return False, float('inf')
        distance = float(np.linalg.norm(stored - live))
        return distance < threshold, distance