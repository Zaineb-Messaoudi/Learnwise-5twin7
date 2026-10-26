from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User,
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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'get_full_name', 'role', 'is_active', 'is_staff', 'email_verified', 'two_factor_enabled', 'is_locked', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser', 'email_verified', 'two_factor_enabled', 'date_joined']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-date_joined']
    readonly_fields = ['date_joined', 'last_login', 'email_verified', 'password_changed_at', 'totp_secret', 'backup_codes', 'failed_login_attempts', 'locked_until']

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'avatar', 'phone', 'bio')}),
        ('Roles & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'email_verified')}),
        ('Security', {'fields': ('two_factor_enabled', 'failed_login_attempts', 'locked_until', 'password_changed_at')}),
        ('Terms & Consent', {'fields': ('terms_accepted_at', 'terms_version', 'privacy_accepted_at', 'marketing_consent', 'marketing_consent_at')}),
        ('Email Change', {'fields': ('pending_email', 'email_change_token', 'email_change_requested_at')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    def get_full_name(self, obj):
        return obj.name
    get_full_name.short_description = 'Full Name'

    def is_locked(self, obj):
        if obj.is_locked():
            return format_html('<span style="color: red;">✓ Locked</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    is_locked.short_description = 'Lock Status'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'created_at', 'verified_at', 'is_valid_display']
    list_filter = ['verified_at', 'created_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['token', 'created_at', 'verified_at']
    ordering = ['-created_at']

    def is_valid_display(self, obj):
        if obj.verified_at:
            return format_html('<span style="color: green;">✓ Verified</span>')
        elif obj.is_valid():
            return format_html('<span style="color: orange;">⏳ Pending</span>')
        else:
            return format_html('<span style="color: red;">✗ Expired</span>')
    is_valid_display.short_description = 'Status'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'created_at', 'used_at', 'is_valid_display']
    list_filter = ['used_at', 'created_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['token', 'created_at', 'used_at']
    ordering = ['-created_at']

    def is_valid_display(self, obj):
        if obj.used_at:
            return format_html('<span style="color: green;">✓ Used</span>')
        elif obj.is_valid():
            return format_html('<span style="color: orange;">⏳ Valid</span>')
        else:
            return format_html('<span style="color: red;">✗ Expired</span>')
    is_valid_display.short_description = 'Status'


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'provider_user_id', 'created_at']
    list_filter = ['provider', 'created_at']
    search_fields = ['user__email', 'provider_user_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_name', 'ip_address', 'is_current', 'created_at', 'last_activity', 'revoked_at']
    list_filter = ['is_current', 'created_at', 'revoked_at']
    search_fields = ['user__email', 'session_key', 'ip_address']
    readonly_fields = ['user', 'session_key', 'ip_address', 'user_agent', 'device_info', 'location', 'created_at', 'last_activity', 'revoked_at']
    ordering = ['-last_activity']

    def device_name(self, obj):
        return obj.device_info.get('browser', 'Unknown') if obj.device_info else 'Unknown'
    device_name.short_description = 'Device'


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'event_type', 'severity', 'ip_address', 'created_at']
    list_filter = ['event_type', 'severity', 'created_at']
    search_fields = ['user__email', 'description']
    readonly_fields = ['user', 'event_type', 'severity', 'description', 'ip_address', 'user_agent', 'metadata', 'created_at']
    ordering = ['-created_at']
    actions = []


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'resource_type', 'resource_id', 'ip_address', 'created_at']
    list_filter = ['action', 'resource_type', 'created_at']
    search_fields = ['user__email', 'description', 'resource_id']
    readonly_fields = ['user', 'action', 'resource_type', 'resource_id', 'description', 'ip_address', 'user_agent', 'metadata', 'created_at']
    ordering = ['-created_at']
    actions = []


@admin.register(DataExportRequest)
class DataExportRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'file_size', 'requested_at', 'completed_at']
    list_filter = ['status', 'requested_at', 'completed_at']
    search_fields = ['user__email']
    readonly_fields = ['user', 'file_path', 'file_size', 'requested_at', 'completed_at', 'expires_at', 'error_message']
    ordering = ['-requested_at']


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'requested_at', 'confirmed_at', 'scheduled_deletion_at', 'completed_at']
    list_filter = ['status', 'requested_at', 'confirmed_at', 'completed_at']
    search_fields = ['user__email', 'reason']
    readonly_fields = ['user', 'confirmation_token', 'reason', 'feedback', 'requested_at', 'confirmed_at', 'scheduled_deletion_at', 'completed_at', 'cancelled_at']
    ordering = ['-requested_at']


@admin.register(TermsVersion)
class TermsVersionAdmin(admin.ModelAdmin):
    list_display = ['version', 'title', 'effective_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'effective_date']
    search_fields = ['version', 'title']
    readonly_fields = ['created_at']