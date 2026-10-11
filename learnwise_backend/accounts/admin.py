from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, EmailVerification, PasswordResetToken, SocialAccount


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'get_full_name', 'role', 'is_active', 'is_staff', 'email_verified', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser', 'email_verified', 'date_joined']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-date_joined']
    readonly_fields = ['date_joined', 'last_login', 'email_verified']

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'avatar', 'phone', 'bio')}),
        ('Roles & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'email_verified')}),
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