from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    EmailVerificationView,
    VerifyCodeView,
    ResendVerificationView,
    PublicResendVerificationView,
    SocialAuthView,
    SelectRoleView,
    TwoFactorSetupView,
    TwoFactorDisableView,
    EmailChangeRequestView,
    EmailChangeConfirmView,
    UserSessionListView,
    RevokeSessionView,
    RevokeAllSessionsView,
    AvatarUploadView,
    AvatarRemoveView,
    FaceRegisterView,
    FaceVerifyView,
    FaceProfileView,
    StepUpView,
    SecurityEventListView,
    ActivityLogListView,
    TermsVersionView,
    TermsAcceptView,
    PrivacyAcceptView,
    DataExportRequestView,
    DataExportDownloadView,
    AccountDeletionRequestView,
    AccountDeletionConfirmView,
    CancelDeletionView,
    AdminUserViewSet,
    SessionAwareTokenRefreshView,
)

# Admin router for user management
admin_router = DefaultRouter()
admin_router.register(r'', AdminUserViewSet, basename='admin-users')

# Authentication endpoints - included under /api/v1/auth/
auth_urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', SessionAwareTokenRefreshView.as_view(), name='token-refresh'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('verify-email/', EmailVerificationView.as_view(), name='verify-email'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('resend-verification/', PublicResendVerificationView.as_view(), name='resend-verification-public'),
    path('social/', SocialAuthView.as_view(), name='social-auth'),
    path('select-role/', SelectRoleView.as_view(), name='select-role'),
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='2fa-setup'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='2fa-disable'),
    path('email-change/', EmailChangeRequestView.as_view(), name='email-change-request'),
    path('email-change/confirm/', EmailChangeConfirmView.as_view(), name='email-change-confirm'),
    path('face/register/', FaceRegisterView.as_view(), name='face-register'),
    path('face/verify/', FaceVerifyView.as_view(), name='face-verify'),
    path('face/profile/', FaceProfileView.as_view(), name='face-profile'),
    path('step-up/', StepUpView.as_view(), name='step-up'),
    path('sessions/', UserSessionListView.as_view(), name='sessions'),
    path('sessions/<int:session_id>/revoke/', RevokeSessionView.as_view(), name='session-revoke'),
    path('sessions/revoke-all/', RevokeAllSessionsView.as_view(), name='sessions-revoke-all'),
    path('security-events/', SecurityEventListView.as_view(), name='security-events'),
    path('activity-logs/', ActivityLogListView.as_view(), name='activity-logs'),
    path('data-export/', DataExportRequestView.as_view(), name='data-export'),
    path('data-export/<int:export_id>/download/', DataExportDownloadView.as_view(), name='data-export-download'),
    path('deletion-request/', AccountDeletionRequestView.as_view(), name='deletion-request'),
    path('deletion/confirm/', AccountDeletionConfirmView.as_view(), name='deletion-confirm'),
    path('deletion/cancel/', CancelDeletionView.as_view(), name='deletion-cancel'),
]

# Account management endpoints - included under /api/v1/accounts/
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
    path('avatar/remove/', AvatarRemoveView.as_view(), name='avatar-remove'),
    path('terms/', TermsVersionView.as_view(), name='terms'),
    path('terms/accept/', TermsAcceptView.as_view(), name='terms-accept'),
    path('privacy/accept/', PrivacyAcceptView.as_view(), name='privacy-accept'),
    path('admin/users/', include(admin_router.urls)),
]

# Re-export auth_urlpatterns for the main urls.py to include
__all__ = ['urlpatterns', 'auth_urlpatterns']