import base64
import hashlib
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = [
        ('etudiant', 'Étudiant'),
        ('professeur', 'Professeur'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='etudiant')
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

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def record_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=30)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def record_successful_login(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def add_password_to_history(self, password_hash):
        history = self.password_history or []
        history.insert(0, password_hash)
        self.password_history = history[:10]
        self.password_changed_at = timezone.now()
        self.save(update_fields=['password_history', 'password_changed_at'])

    def check_password_history(self, password):
        for old_hash in self.password_history:
            if self.check_password(password):
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
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)

    def generate_backup_codes(self, count=10):
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        self.backup_codes = codes
        self.save(update_fields=['backup_codes'])
        return codes

    def use_backup_code(self, code):
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save(update_fields=['backup_codes'])
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
            self.email = self.pending_email
            self.username = self.pending_email.split('@')[0]
            self.pending_email = None
            self.email_change_token = None
            self.email_change_requested_at = None
            self.email_verified = False
            self.save(update_fields=['email', 'username', 'pending_email', 'email_change_token', 'email_change_requested_at', 'email_verified'])
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
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_email_verification'

    def __str__(self):
        return f"Email verification for {self.user.email}"

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

    def __str__(self):
        return f"{self.user.email} - {self.provider}"


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
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

    def __str__(self):
        return f"Terms v{self.version}"