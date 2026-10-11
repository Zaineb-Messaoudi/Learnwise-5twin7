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
