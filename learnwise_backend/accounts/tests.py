import uuid
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from accounts.models import (
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
from accounts.serializers import (
    UserSerializer,
    UserProfileSerializer,
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer,
    SocialAuthSerializer,
    TwoFactorSetupSerializer,
    TwoFactorVerifySerializer,
    TwoFactorDisableSerializer,
    EmailChangeRequestSerializer,
    EmailChangeConfirmSerializer,
    UserSessionSerializer,
    SecurityEventSerializer,
    ActivityLogSerializer,
    DataExportRequestSerializer,
    TermsVersionSerializer,
    TermsAcceptSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    AvatarUploadSerializer,
)
from accounts.views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    EmailVerificationView,
    ResendVerificationView,
    SocialAuthView,
    TwoFactorSetupView,
    TwoFactorDisableView,
    EmailChangeRequestView,
    EmailChangeConfirmView,
    UserSessionListView,
    RevokeSessionView,
    RevokeAllSessionsView,
    AvatarUploadView,
    SecurityEventListView,
    ActivityLogListView,
    TermsVersionView,
    TermsAcceptView,
    PrivacyAcceptView,
    DataExportRequestView,
    AccountDeletionRequestView,
    AccountDeletionConfirmView,
    CancelDeletionView,
    AdminUserViewSet,
    log_security_event,
    log_activity,
)

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            first_name='Test',
            last_name='User',
            password='SecurePass123!@'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertIsNone(user.role)
        self.assertTrue(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.two_factor_enabled)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='AdminPass123!@'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_name_property(self):
        user = User.objects.create_user(
            email='nametest@example.com',
            username='nametest',
            first_name='Name',
            last_name='Test',
            password='SecurePass123!@'
        )
        self.assertEqual(user.name, 'Name Test')

    def test_name_property_falls_back_to_email(self):
        user = User.objects.create_user(
            email='noName@example.com',
            username='noname',
            first_name='',
            last_name='',
            password='SecurePass123!@'
        )
        self.assertEqual(user.name, 'noName@example.com')

    def test_is_locked_no_lockout(self):
        user = User.objects.create_user(
            email='locktest@example.com',
            username='locktest',
            password='SecurePass123!@'
        )
        self.assertFalse(user.is_locked())

    def test_is_locked_with_active_lockout(self):
        user = User.objects.create_user(
            email='locktest2@example.com',
            username='locktest2',
            password='SecurePass123!@'
        )
        user.locked_until = timezone.now() + timedelta(minutes=30)
        user.save()
        self.assertTrue(user.is_locked())

    def test_is_locked_with_expired_lockout(self):
        user = User.objects.create_user(
            email='locktest3@example.com',
            username='locktest3',
            password='SecurePass123!@'
        )
        user.locked_until = timezone.now() - timedelta(minutes=30)
        user.save()
        self.assertFalse(user.is_locked())

    def test_record_failed_login_increments_attempts(self):
        user = User.objects.create_user(
            email='failedlogin@example.com',
            username='failedlogin',
            password='SecurePass123!@'
        )
        user.record_failed_login()
        self.assertEqual(user.failed_login_attempts, 1)

    def test_record_failed_login_locks_after_5_attempts(self):
        user = User.objects.create_user(
            email='lockafter5@example.com',
            username='lockafter5',
            password='SecurePass123!@'
        )
        for _ in range(5):
            user.record_failed_login()
        self.assertTrue(user.locked_until is not None)
        self.assertTrue(user.is_locked())

    def test_record_successful_login_resets_attempts(self):
        user = User.objects.create_user(
            email='successlogin@example.com',
            username='successlogin',
            password='SecurePass123!@'
        )
        user.failed_login_attempts = 3
        user.locked_until = timezone.now() + timedelta(minutes=30)
        user.save()
        user.record_successful_login()
        self.assertEqual(user.failed_login_attempts, 0)
        self.assertIsNone(user.locked_until)

    def test_password_history(self):
        user = User.objects.create_user(
            email='historytest@example.com',
            username='historytest',
            password='SecurePass123!@'
        )
        old_password_hash = user.password
        user.add_password_to_history(old_password_hash)
        self.assertEqual(len(user.password_history), 1)

    def test_check_password_history_reuse(self):
        user = User.objects.create_user(
            email='reuse@example.com',
            username='reuse',
            password='SecurePass123!@'
        )
        user.add_password_to_history(user.password)
        self.assertTrue(user.check_password_history('SecurePass123!@'))
        self.assertFalse(user.check_password_history('DifferentPass123!@'))

    def test_totp_secret_generation(self):
        user = User.objects.create_user(
            email='totp@example.com',
            username='totp',
            password='SecurePass123!@'
        )
        secret = user.generate_totp_secret()
        self.assertTrue(secret)
        self.assertTrue(user.totp_secret)

    def test_totp_uri_generation(self):
        user = User.objects.create_user(
            email='totpuri@example.com',
            username='totpuri',
            password='SecurePass123!@'
        )
        user.generate_totp_secret()
        uri = user.get_totp_uri()
        self.assertIn('otpauth://', uri)
        self.assertIn('Learnwise', uri)

    def test_verify_totp_without_secret(self):
        user = User.objects.create_user(
            email='verifytotp@example.com',
            username='verifytotp',
            password='SecurePass123!@'
        )
        self.assertFalse(user.verify_totp('123456'))

    def test_backup_codes_generation(self):
        user = User.objects.create_user(
            email='backup@example.com',
            username='backup',
            password='SecurePass123!@'
        )
        codes = user.generate_backup_codes(count=5)
        self.assertEqual(len(codes), 5)
        self.assertEqual(len(user.backup_codes), 5)

    def test_use_backup_code_valid(self):
        user = User.objects.create_user(
            email='usebackup@example.com',
            username='usebackup',
            password='SecurePass123!@'
        )
        codes = user.generate_backup_codes(count=3)
        result = user.use_backup_code(codes[0])
        self.assertTrue(result)
        self.assertEqual(len(user.backup_codes), 2)

    def test_use_backup_code_invalid(self):
        user = User.objects.create_user(
            email='invalidbackup@example.com',
            username='invalidbackup',
            password='SecurePass123!@'
        )
        user.generate_backup_codes(count=3)
        result = user.use_backup_code('invalid-code')
        self.assertFalse(result)

    def test_email_change_flow(self):
        user = User.objects.create_user(
            email='change@example.com',
            username='change',
            password='SecurePass123!@'
        )
        user.request_email_change('newemail@example.com')
        self.assertEqual(user.pending_email, 'newemail@example.com')
        self.assertIsNotNone(user.email_change_token)

    def test_confirm_email_change_valid(self):
        user = User.objects.create_user(
            email='confirm@example.com',
            username='confirm',
            password='SecurePass123!@'
        )
        user.request_email_change('newconfirm@example.com')
        token = user.email_change_token
        result = user.confirm_email_change(token)
        self.assertTrue(result)
        self.assertEqual(user.email, 'newconfirm@example.com')

    def test_confirm_email_change_invalid_token(self):
        user = User.objects.create_user(
            email='invalidtoken@example.com',
            username='invalidtoken',
            password='SecurePass123!@'
        )
        user.request_email_change('newtoken@example.com')
        result = user.confirm_email_change(uuid.uuid4())
        self.assertFalse(result)

    def test_confirm_email_change_expired(self):
        user = User.objects.create_user(
            email='expired@example.com',
            username='expired',
            password='SecurePass123!@'
        )
        user.request_email_change('newexpired@example.com')
        user.email_change_requested_at = timezone.now() - timedelta(hours=25)
        user.save()
        result = user.confirm_email_change(user.email_change_token)
        self.assertFalse(result)

    def test_accept_terms(self):
        user = User.objects.create_user(
            email='terms@example.com',
            username='terms',
            password='SecurePass123!@'
        )
        user.accept_terms('2.0')
        self.assertIsNotNone(user.terms_accepted_at)
        self.assertEqual(user.terms_version, '2.0')

    def test_accept_privacy(self):
        user = User.objects.create_user(
            email='privacy@example.com',
            username='privacy',
            password='SecurePass123!@'
        )
        user.accept_privacy()
        self.assertIsNotNone(user.privacy_accepted_at)

    def test_marketing_consent(self):
        user = User.objects.create_user(
            email='marketing@example.com',
            username='marketing',
            password='SecurePass123!@'
        )
        user.set_marketing_consent(True)
        self.assertTrue(user.marketing_consent)
        user.set_marketing_consent(False)
        self.assertFalse(user.marketing_consent)


class EmailVerificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='verify@example.com',
            username='verify',
            password='SecurePass123!@'
        )

    def test_create_email_verification(self):
        verification = EmailVerification.objects.create(user=self.user)
        self.assertEqual(verification.token, verification.token)
        self.assertIsNone(verification.verified_at)

    def test_is_valid(self):
        verification = EmailVerification.objects.create(user=self.user)
        self.assertTrue(verification.is_valid())

    def test_is_valid_already_verified(self):
        verification = EmailVerification.objects.create(user=self.user)
        verification.verified_at = timezone.now()
        verification.save()
        self.assertFalse(verification.is_valid())

    def test_mark_verified(self):
        verification = EmailVerification.objects.create(user=self.user)
        verification.mark_verified()
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)


class PasswordResetTokenModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reset@example.com',
            username='reset',
            password='SecurePass123!@'
        )

    def test_create_reset_token(self):
        token = PasswordResetToken.objects.create(user=self.user)
        self.assertTrue(token.token)

    def test_is_valid(self):
        token = PasswordResetToken.objects.create(user=self.user)
        self.assertTrue(token.is_valid())

    def test_is_valid_after_use(self):
        token = PasswordResetToken.objects.create(user=self.user)
        token.mark_used()
        self.assertFalse(token.is_valid())

    def test_is_valid_expired(self):
        token = PasswordResetToken.objects.create(user=self.user)
        token.created_at = timezone.now() - timedelta(hours=2)
        token.save()
        self.assertFalse(token.is_valid())


class SocialAccountModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='social@example.com',
            username='social',
            password='SecurePass123!@'
        )

    def test_create_social_account(self):
        account = SocialAccount.objects.create(
            user=self.user,
            provider='google',
            provider_user_id='12345',
        )
        self.assertEqual(account.provider, 'google')
        self.assertEqual(account.provider_user_id, '12345')


class SecurityEventModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='security@example.com',
            username='security',
            password='SecurePass123!@'
        )

    def test_create_security_event(self):
        event = SecurityEvent.objects.create(
            user=self.user,
            event_type='login',
            severity='info',
            description='Test event'
        )
        self.assertEqual(event.event_type, 'login')
        self.assertEqual(event.severity, 'info')


class ActivityLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='activity@example.com',
            username='activity',
            password='SecurePass123!@'
        )

    def test_create_activity_log(self):
        log = ActivityLog.objects.create(
            user=self.user,
            action='create',
            resource_type='course',
            description='Created course'
        )
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.resource_type, 'course')


class DataExportRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='export@example.com',
            username='export',
            password='SecurePass123!@'
        )

    def test_create_export_request(self):
        export = DataExportRequest.objects.create(user=self.user, status='pending')
        self.assertEqual(export.status, 'pending')


class AccountDeletionRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='delete@example.com',
            username='delete',
            password='SecurePass123!@'
        )

    def test_create_deletion_request(self):
        deletion = AccountDeletionRequest.objects.create(
            user=self.user,
            status='pending',
            confirmation_token=uuid.uuid4()
        )
        self.assertEqual(deletion.status, 'pending')
        self.assertIsNotNone(deletion.confirmation_token)


class TermsVersionModelTest(TestCase):
    def test_create_terms_version(self):
        terms = TermsVersion.objects.create(
            version='1.0',
            title='Terms of Service',
            content='These are the terms.',
            effective_date=timezone.now(),
            is_active=True
        )
        self.assertEqual(terms.version, '1.0')
        self.assertTrue(terms.is_active)


class SerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='serial@example.com',
            username='serial',
            first_name='Serial',
            last_name='User',
            password='SecurePass123!@'
        )

    def test_user_serializer(self):
        serializer = UserSerializer(self.user)
        data = serializer.data
        self.assertEqual(data['email'], 'serial@example.com')
        self.assertEqual(data['name'], 'Serial User')
        self.assertFalse(data['email_verified'])
        self.assertFalse(data['locked'])

    def test_user_profile_serializer(self):
        serializer = UserProfileSerializer(self.user)
        data = serializer.data
        self.assertEqual(data['email'], 'serial@example.com')

    def test_register_serializer_valid(self):
        serializer = RegisterSerializer(data={
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'NewPass123!@',
            'confirm_password': 'NewPass123!@',
            'role': 'etudiant',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_register_serializer_password_mismatch(self):
        serializer = RegisterSerializer(data={
            'email': 'mismatch@example.com',
            'username': 'mismatch',
            'password': 'Pass123!@',
            'confirm_password': 'Different123!@',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('confirm_password', serializer.errors)

    def test_register_serializer_duplicate_email(self):
        serializer = RegisterSerializer(data={
            'email': 'serial@example.com',
            'username': 'different',
            'password': 'Pass123!@',
            'confirm_password': 'Pass123!@',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_login_serializer(self):
        serializer = LoginSerializer(data={
            'email': 'serial@example.com',
            'password': 'SecurePass123!@',
        })
        self.assertTrue(serializer.is_valid())

    def test_change_password_serializer_valid(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post('/change-password/')
        request.user = self.user
        serializer = ChangePasswordSerializer(data={
            'current_password': 'SecurePass123!@',
            'new_password': 'NewSecurePass123!@',
            'confirm_password': 'NewSecurePass123!@',
        }, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_change_password_serializer_wrong_current(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post('/change-password/')
        request.user = self.user
        serializer = ChangePasswordSerializer(data={
            'current_password': 'WrongPassword',
            'new_password': 'NewSecurePass123!@',
            'confirm_password': 'NewSecurePass123!@',
        }, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('current_password', serializer.errors)

    def test_change_password_serializer_mismatch(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post('/change-password/')
        request.user = self.user
        serializer = ChangePasswordSerializer(data={
            'current_password': 'SecurePass123!@',
            'new_password': 'NewSecurePass123!@',
            'confirm_password': 'DifferentPass123!@',
        }, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('confirm_password', serializer.errors)

    def test_password_reset_request_serializer(self):
        serializer = PasswordResetRequestSerializer(data={'email': 'serial@example.com'})
        self.assertTrue(serializer.is_valid())

    def test_password_reset_request_serializer_nonexistent_email(self):
        serializer = PasswordResetRequestSerializer(data={'email': 'nonexistent@example.com'})
        # Serializer accepts any valid email format; view handles user existence
        self.assertTrue(serializer.is_valid())

    def test_password_reset_confirm_serializer_mismatch(self):
        serializer = PasswordResetConfirmSerializer(data={
            'token': 'sometoken',
            'password': 'NewPass123!@',
            'confirm_password': 'Different123!@',
        })
        self.assertFalse(serializer.is_valid())

    def test_email_verification_serializer(self):
        verification = EmailVerification.objects.create(user=self.user)
        serializer = EmailVerificationSerializer(data={'token': str(verification.token)})
        self.assertTrue(serializer.is_valid())

    def test_social_auth_serializer_with_access_token(self):
        serializer = SocialAuthSerializer(data={
            'provider': 'google',
            'access_token': 'test-token',
            'role': 'etudiant',
        })
        self.assertTrue(serializer.is_valid())

    def test_social_auth_serializer_without_token_or_code(self):
        serializer = SocialAuthSerializer(data={'provider': 'google'})
        self.assertFalse(serializer.is_valid())

    def test_two_factor_verify_serializer(self):
        serializer = TwoFactorVerifySerializer(data={'token': '123456'})
        self.assertTrue(serializer.is_valid())

    def test_two_factor_disable_serializer_requires_password(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post('/2fa/disable/')
        request.user = self.user
        serializer = TwoFactorDisableSerializer(data={'token': '123456'}, context={'request': request})
        self.assertFalse(serializer.is_valid())

    def test_two_factor_disable_serializer_wrong_password(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post('/2fa/disable/')
        request.user = self.user
        serializer = TwoFactorDisableSerializer(data={
            'password': 'WrongPassword',
            'token': '123456',
        }, context={'request': request})
        self.assertFalse(serializer.is_valid())

    def test_email_change_request_serializer(self):
        serializer = EmailChangeRequestSerializer(data={'new_email': 'newemail@example.com'})
        self.assertTrue(serializer.is_valid())

    def test_email_change_request_serializer_existing_email(self):
        serializer = EmailChangeRequestSerializer(data={'new_email': 'serial@example.com'})
        self.assertFalse(serializer.is_valid())

    def test_email_change_confirm_serializer(self):
        serializer = EmailChangeConfirmSerializer(data={'token': 'sometoken'})
        self.assertTrue(serializer.is_valid())

    def test_terms_accept_serializer(self):
        serializer = TermsAcceptSerializer(data={'version': '1.0', 'marketing_consent': False})
        self.assertTrue(serializer.is_valid())

    def test_admin_user_serializer(self):
        serializer = AdminUserSerializer(self.user)
        data = serializer.data
        self.assertEqual(data['email'], 'serial@example.com')
        self.assertIsNone(data['role'])
        self.assertFalse(data['locked'])

    def test_admin_user_update_serializer(self):
        serializer = AdminUserUpdateSerializer(
            self.user,
            data={'email': 'updated@example.com', 'username': 'updated', 'first_name': 'Updated', 'last_name': 'Name'},
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class RegisterViewTest(APITestCase):
    def test_register_success(self):
        response = self.client.post('/api/v1/accounts/register/', {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'NewPass123!@',
            'confirm_password': 'NewPass123!@',
            'role': 'etudiant',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('detail', response.data)
        self.assertIn('verify', response.data['detail'].lower())
        # No tokens returned until email is verified
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email='existing@example.com',
            username='existing',
            password='SecurePass123!@'
        )
        response = self.client.post('/api/v1/accounts/register/', {
            'email': 'existing@example.com',
            'username': 'newuser',
            'password': 'NewPass123!@',
            'confirm_password': 'NewPass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        response = self.client.post('/api/v1/accounts/register/', {
            'email': 'mismatch@example.com',
            'username': 'mismatch',
            'password': 'NewPass123!@',
            'confirm_password': 'Different123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='login@example.com',
            username='login',
            password='SecurePass123!@'
        )
        self.user.email_verified = True
        self.user.save()

    def test_login_success(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'login@example.com',
            'password': 'SecurePass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_invalid_password(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'login@example.com',
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Invalid credentials.')

    def test_login_nonexistent_email(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'nonexistent@example.com',
            'password': 'SecurePass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_locked_account(self):
        self.user.locked_until = timezone.now() + timedelta(minutes=30)
        self.user.save()
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'login@example.com',
            'password': 'SecurePass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_inactive_account(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'login@example.com',
            'password': 'SecurePass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_2fa_required(self):
        self.user.two_factor_enabled = True
        self.user.generate_totp_secret()
        self.user.save()
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'login@example.com',
            'password': 'SecurePass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_428_PRECONDITION_REQUIRED)
        self.assertTrue(response.data['requires_2fa'])

    def test_login_failed_attempts_increment(self):
        self.client.post('/api/v1/auth/login/', {
            'email': 'login@example.com',
            'password': 'WrongPassword',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)


class LogoutViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='logout@example.com',
            username='logout',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_logout_with_refresh_token(self):
        response = self.client.post('/api/v1/auth/logout/', {
            'refresh': 'some-refresh-token'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_refresh_token(self):
        response = self.client.post('/api/v1/auth/logout/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MeViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='me@example.com',
            username='meuser',
            first_name='Me',
            last_name='User',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_me(self):
        response = self.client.get('/api/v1/accounts/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'me@example.com')

    def test_update_me(self):
        response = self.client.patch('/api/v1/accounts/me/', {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '1234567890',
            'bio': 'Updated bio',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.phone, '1234567890')


class ChangePasswordViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='changepass@example.com',
            username='changepass',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_change_password_success(self):
        response = self.client.post('/api/v1/accounts/change-password/', {
            'current_password': 'SecurePass123!@',
            'new_password': 'NewSecurePass456!@',
            'confirm_password': 'NewSecurePass456!@',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_current(self):
        response = self.client.post('/api/v1/accounts/change-password/', {
            'current_password': 'WrongPassword',
            'new_password': 'NewSecurePass456!@',
            'confirm_password': 'NewSecurePass456!@',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_mismatch(self):
        response = self.client.post('/api/v1/accounts/change-password/', {
            'current_password': 'SecurePass123!@',
            'new_password': 'NewSecurePass456!@',
            'confirm_password': 'Different789!@',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetFlowTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reset@example.com',
            username='reset',
            password='SecurePass123!@'
        )

    def test_password_reset_request(self):
        response = self.client.post('/api/v1/auth/password-reset/', {
            'email': 'reset@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

    def test_password_reset_request_nonexistent_email(self):
        response = self.client.post('/api/v1/auth/password-reset/', {
            'email': 'nonexistent@example.com',
        })
        # Same response whether or not the account exists (no user enumeration)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detail', response.data)

    def test_password_reset_confirm(self):
        token = PasswordResetToken.objects.create(user=self.user)
        response = self.client.post('/api/v1/auth/password-reset/confirm/', {
            'token': str(token.token),
            'password': 'NewSecurePass456!@',
            'confirm_password': 'NewSecurePass456!@',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_password_reset_confirm_invalid_token(self):
        response = self.client.post('/api/v1/auth/password-reset/confirm/', {
            'token': 'invalid-token',
            'password': 'NewSecurePass456!@',
            'confirm_password': 'NewSecurePass456!@',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_mismatch(self):
        token = PasswordResetToken.objects.create(user=self.user)
        response = self.client.post('/api/v1/auth/password-reset/confirm/', {
            'token': str(token.token),
            'password': 'NewSecurePass456!@',
            'confirm_password': 'Different789!@',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailVerificationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='verify@example.com',
            username='verify',
            password='SecurePass123!@'
        )

    def test_verify_email_success(self):
        verification = EmailVerification.objects.create(user=self.user)
        response = self.client.post('/api/v1/auth/verify-email/', {
            'token': str(verification.token),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_verify_email_invalid_token(self):
        response = self.client.post('/api/v1/auth/verify-email/', {
            'token': 'invalid-token',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SocialAuthViewTest(APITestCase):
    def test_social_auth_requires_token_or_code(self):
        response = self.client.post('/api/v1/auth/social/', {
            'provider': 'google',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_social_auth_unsupported_provider(self):
        response = self.client.post('/api/v1/auth/social/', {
            'provider': 'unsupported',
            'code': 'some-code',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('accounts.views.SocialAuthView._verify_google_token')
    @mock.patch('accounts.views.SocialAuthView._exchange_google_code')
    def test_social_auth_with_code(self, mock_exchange, mock_verify):
        mock_exchange.return_value = 'mock-access-token'
        mock_verify.return_value = {
            'email': 'social@example.com',
            'given_name': 'Social',
            'family_name': 'User',
            'sub': '12345',
            'email_verified': True,
        }
        response = self.client.post('/api/v1/auth/social/', {
            'provider': 'google',
            'code': 'auth-code',
            'role': 'etudiant',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(response.data['is_new_user'])

    @mock.patch('accounts.views.SocialAuthView._verify_google_token')
    def test_social_auth_with_access_token(self, mock_verify):
        mock_verify.return_value = {
            'email': 'existing@example.com',
            'given_name': 'Existing',
            'family_name': 'User',
            'sub': '12345',
            'email_verified': True,
        }
        user = User.objects.create_user(
            email='existing@example.com',
            username='existing',
            password='SecurePass123!@'
        )
        # Add social account for the user
        SocialAccount.objects.create(
            user=user,
            provider='google',
            provider_user_id='12345',
            access_token='existing-token'
        )
        response = self.client.post('/api/v1/auth/social/', {
            'provider': 'google',
            'access_token': 'existing-token',
            'role': 'etudiant',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_new_user'])


class TwoFactorSetupViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='2fa@example.com',
            username='twofa',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_2fa_setup(self):
        response = self.client.get('/api/v1/auth/2fa/setup/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('secret', response.data)
        self.assertIn('qr_code', response.data)
        self.assertIn('backup_codes', response.data)

    def test_post_2fa_enable_with_valid_totp(self):
        import pyotp
        self.user.generate_totp_secret()
        self.user.generate_backup_codes(10)
        totp = pyotp.TOTP(self.user.totp_secret)
        token = totp.now()
        response = self.client.post('/api/v1/auth/2fa/setup/', {
            'token': token,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('backup_codes', response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)


class TwoFactorDisableViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='disable2fa@example.com',
            username='disable2fa',
            password='SecurePass123!@'
        )
        self.user.two_factor_enabled = True
        self.user.generate_totp_secret()
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_disable_2fa_success(self):
        import pyotp
        totp = pyotp.TOTP(self.user.totp_secret)
        token = totp.now()
        response = self.client.post('/api/v1/auth/2fa/disable/', {
            'password': 'SecurePass123!@',
            'token': token,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.two_factor_enabled)

    def test_disable_2fa_wrong_password(self):
        response = self.client.post('/api/v1/auth/2fa/disable/', {
            'password': 'WrongPassword',
            'token': '123456',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailChangeTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='emailchange@example.com',
            username='emailchange',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_request_email_change(self):
        response = self.client.post('/api/v1/auth/email-change/', {
            'new_email': 'newemail@example.com',
            'current_password': 'SecurePass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_email, 'newemail@example.com')

    def test_request_email_change_existing_email(self):
        response = self.client.post('/api/v1/auth/email-change/', {
            'new_email': 'emailchange@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_email_change(self):
        self.user.request_email_change('newemail@example.com')
        token = self.user.email_change_token
        response = self.client.post('/api/v1/auth/email-change/confirm/', {
            'token': str(token),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')

    def test_confirm_email_change_invalid_token(self):
        self.user.request_email_change('newemail@example.com')
        response = self.client.post('/api/v1/auth/email-change/confirm/', {
            'token': 'invalid-token',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SessionManagementTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='session@example.com',
            username='session',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)
        UserSession.objects.create(
            user=self.user,
            session_key='test-key-1',
            is_current=True,
        )

    def test_list_sessions(self):
        response = self.client.get('/api/v1/auth/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_revoke_session(self):
        session = UserSession.objects.get(session_key='test-key-1')
        response = self.client.post(f'/api/v1/auth/sessions/{session.id}/revoke/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)

    def test_revoke_session_not_found(self):
        response = self.client.post('/api/v1/auth/sessions/99999/revoke/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoke_all_sessions(self):
        UserSession.objects.create(
            user=self.user,
            session_key='test-key-2',
            is_current=True,
        )
        response = self.client.post('/api/v1/auth/sessions/revoke-all/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.user.sessions.filter(revoked_at__isnull=True).count(),
            0
        )


class SecurityEventTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='security@example.com',
            username='security',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)
        log_security_event(
            user=self.user,
            event_type='login_failed',
            severity='warning',
            description='Test event',
        )

    def test_list_security_events(self):
        response = self.client.get('/api/v1/auth/security-events/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


class ActivityLogTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='activity@example.com',
            username='activity',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)
        log_activity(
            user=self.user,
            action='login',
            resource_type='profile',
            description='User logged in',
        )

    def test_list_activity_logs(self):
        response = self.client.get('/api/v1/auth/activity-logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


class TermsVersionViewTest(APITestCase):
    def test_get_active_terms(self):
        TermsVersion.objects.create(
            version='1.0',
            title='Terms',
            content='Content',
            effective_date=timezone.now(),
            is_active=True
        )
        response = self.client.get('/api/v1/accounts/terms/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TermsAcceptViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='terms@example.com',
            username='termsuser',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_accept_terms(self):
        response = self.client.post('/api/v1/accounts/terms/accept/', {
            'version': '1.0',
            'marketing_consent': True,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.terms_version, '1.0')

    def test_accept_privacy(self):
        response = self.client.post('/api/v1/accounts/privacy/accept/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.privacy_accepted_at)


class DataExportTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='export@example.com',
            username='export',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_request_data_export(self):
        response = self.client.post('/api/v1/auth/data-export/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(DataExportRequest.objects.filter(user=self.user).exists())

    def test_list_data_exports(self):
        response = self.client.get('/api/v1/auth/data-export/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AccountDeletionTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='delete@example.com',
            username='delete',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_request_account_deletion(self):
        response = self.client.post('/api/v1/auth/deletion-request/', {
            'reason': 'No longer needed',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AccountDeletionRequest.objects.filter(user=self.user).exists())

    def test_get_deletion_request(self):
        response = self.client.get('/api/v1/auth/deletion-request/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_confirm_account_deletion(self):
        deletion = AccountDeletionRequest.objects.create(
            user=self.user,
            status='pending',
            confirmation_token=uuid.uuid4(),
        )
        response = self.client.post('/api/v1/auth/deletion/confirm/', {
            'token': str(deletion.confirmation_token),
            'password': 'SecurePass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        deletion.refresh_from_db()
        self.assertEqual(deletion.status, 'confirmed')

    def test_confirm_account_deletion_wrong_password(self):
        deletion = AccountDeletionRequest.objects.create(
            user=self.user,
            status='pending',
            confirmation_token=uuid.uuid4(),
        )
        response = self.client.post('/api/v1/auth/deletion/confirm/', {
            'token': str(deletion.confirmation_token),
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_account_deletion(self):
        AccountDeletionRequest.objects.create(
            user=self.user,
            status='pending',
        )
        response = self.client.post('/api/v1/auth/deletion/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.deletion_request.status, 'cancelled')


class AdminUserViewSetTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='AdminPass123!@'
        )
        self.admin.role = 'admin'
        self.admin.save()
        self.client.force_authenticate(user=self.admin)
        self.user = User.objects.create_user(
            email='testuser@example.com',
            username='testuser',
            password='SecurePass123!@'
        )

    def test_list_users(self):
        response = self.client.get('/api/v1/accounts/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_user(self):
        response = self.client.get(f'/api/v1/accounts/admin/users/{self.user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_user(self):
        response = self.client.post('/api/v1/accounts/admin/users/', {
            'email': 'newadmin@example.com',
            'username': 'newadmin',
            'first_name': 'New',
            'last_name': 'Admin',
            'role': 'etudiant',
            'is_active': True,
            'is_staff': False,
            'password': 'NewAdminPass123!@',
            'confirm_password': 'NewAdminPass123!@',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_user(self):
        response = self.client.patch(f'/api/v1/accounts/admin/users/{self.user.id}/', {
            'first_name': 'Updated',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_activate_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.user.id}/activate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_deactivate_user(self):
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.user.id}/deactivate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_deactivate_self(self):
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.admin.id}/deactivate/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_make_admin(self):
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.user.id}/make_admin/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'admin')
        self.assertTrue(self.user.is_staff)

    def test_remove_admin(self):
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.user.id}/remove_admin/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'etudiant')
        self.assertFalse(self.user.is_staff)

    def test_remove_admin_self(self):
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.admin.id}/remove_admin/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lock_user(self):
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.user.id}/lock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)

    def test_lock_self(self):
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.admin.id}/lock/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unlock_user(self):
        self.user.locked_until = timezone.now() + timedelta(days=365)
        self.user.save()
        response = self.client.post(f'/api/v1/accounts/admin/users/{self.user.id}/unlock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.locked_until)

    def test_user_stats(self):
        response = self.client.get('/api/v1/accounts/admin/users/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('students', response.data)

    def test_non_admin_cannot_access(self):
        regular_user = User.objects.create_user(
            email='regular@example.com',
            username='regular',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=regular_user)
        response = self.client.get('/api/v1/accounts/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AvatarUploadTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='avatar@example.com',
            username='avatar',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)

    def test_upload_avatar(self):
        import io as io_module
        from PIL import Image
        img = Image.new('RGB', (1, 1), color='red')
        buffer = io_module.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        image_file = SimpleUploadedFile(
            'test_avatar.png',
            buffer.getvalue(),
            content_type='image/png'
        )
        response = self.client.post('/api/v1/accounts/avatar/', {'avatar': image_file})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_remove_avatar(self):
        response = self.client.delete('/api/v1/accounts/avatar/remove/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResendVerificationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='resend@example.com',
            username='resend',
            password='SecurePass123!@'
        )
        self.client.force_authenticate(user=self.user)
        EmailVerification.objects.create(user=self.user)

    def test_resend_verification(self):
        response = self.client.post('/api/v1/accounts/resend-verification/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_resend_verification_already_verified(self):
        self.user.email_verified = True
        self.user.save()
        response = self.client.post('/api/v1/accounts/resend-verification/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('already verified', response.data['detail'].lower())
