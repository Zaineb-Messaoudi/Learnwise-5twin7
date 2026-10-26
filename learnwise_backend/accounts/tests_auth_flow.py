"""End-to-end regression tests for the sign-up / sign-in / 2FA / onboarding flow.

They go through the real URLs (not the views directly) so a missing route, a serializer
that rejects what the frontend actually sends, or a permission mismatch is caught.
"""
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import (
    EmailVerification,
    FaceProfile,
    MAX_FAILED_FACE_ATTEMPTS,
    UserSession,
)

User = get_user_model()
DESCRIPTOR = [0.01 * (i % 7) for i in range(128)]


def make_user(email='user@example.com', role='etudiant', password='Str0ng-Pass-123!', **extra):
    extra.setdefault('email_verified', True)
    user = User.objects.create_user(username=email.split('@')[0], email=email, password=password, role=role, **extra)
    return user


def enroll_face(user, descriptor=None):
    return FaceProfile.objects.create(user=user, descriptor=descriptor or DESCRIPTOR, is_verified=True)


class AuthFlowBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()


class RegistrationFlowTests(AuthFlowBase):
    def test_register_with_what_the_signup_form_sends(self):
        # The sign-up form sends no username; role arrives already mapped to the backend value.
        response = self.client.post('/api/v1/accounts/register/', {
            'email': 'New.Student@Example.com',
            'password': 'Str0ng-Pass-123!',
            'confirm_password': 'Str0ng-Pass-123!',
            'first_name': 'New',
            'last_name': 'Student',
            'role': 'etudiant',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email='new.student@example.com')
        self.assertTrue(user.username)
        self.assertFalse(user.email_verified)
        self.assertNotIn('access', response.data)

    def test_register_rejects_admin_role(self):
        response = self.client.post('/api/v1/accounts/register/', {
            'email': 'x@example.com', 'password': 'Str0ng-Pass-123!', 'confirm_password': 'Str0ng-Pass-123!',
            'first_name': 'X', 'last_name': 'Y', 'role': 'admin',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unverified_user_cannot_login_but_can_request_a_new_link_without_a_token(self):
        user = make_user('late@example.com', email_verified=False)
        login = self.client.post('/api/v1/auth/login/', {'email': 'late@example.com', 'password': 'Str0ng-Pass-123!'}, format='json')
        self.assertEqual(login.status_code, status.HTTP_403_FORBIDDEN)

        # Used to be impossible: the only resend endpoint required being logged in.
        resend = self.client.post('/api/v1/auth/resend-verification/', {'email': 'late@example.com'}, format='json')
        self.assertEqual(resend.status_code, status.HTTP_200_OK)
        verification = EmailVerification.objects.get(user=user)

        verify = self.client.post('/api/v1/auth/verify-email/', {'token': str(verification.token)}, format='json')
        self.assertEqual(verify.status_code, status.HTTP_200_OK, verify.data)
        self.assertTrue(verify.data['user']['email_verified'])
        self.assertIn('access', verify.data)

    def test_public_resend_does_not_reveal_whether_the_account_exists(self):
        known = self.client.post('/api/v1/auth/resend-verification/', {'email': make_user('a@example.com').email}, format='json')
        unknown = self.client.post('/api/v1/auth/resend-verification/', {'email': 'nobody@example.com'}, format='json')
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.data, unknown.data)


class TwoFactorFlowTests(AuthFlowBase):
    def _enable_2fa(self, user):
        import pyotp
        self.client.force_authenticate(user)
        setup = self.client.get('/api/v1/auth/2fa/setup/')
        self.assertEqual(setup.status_code, status.HTTP_200_OK)
        code = pyotp.TOTP(setup.data['secret']).now()
        enabled = self.client.post('/api/v1/auth/2fa/setup/', {'token': code}, format='json')
        self.assertEqual(enabled.status_code, status.HTTP_200_OK, enabled.data)
        self.client.force_authenticate(None)
        return enabled.data['backup_codes']

    def test_backup_codes_are_accepted_by_login_exactly_as_displayed(self):
        user = make_user('twofa@example.com')
        codes = self._enable_2fa(user)
        # Displayed as XXXXX-XXXXX (11 chars) â€” the serializer used to cap this at 8 characters.
        self.assertEqual(len(codes[0]), 11)

        response = self.client.post('/api/v1/auth/login/', {
            'email': 'twofa@example.com', 'password': 'Str0ng-Pass-123!', 'backup_code': codes[0],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # A backup code only works once
        again = self.client.post('/api/v1/auth/login/', {
            'email': 'twofa@example.com', 'password': 'Str0ng-Pass-123!', 'backup_code': codes[0],
        }, format='json')
        self.assertEqual(again.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_asks_for_a_second_factor(self):
        user = make_user('ask@example.com')
        self._enable_2fa(user)
        response = self.client.post('/api/v1/auth/login/', {'email': 'ask@example.com', 'password': 'Str0ng-Pass-123!'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_428_PRECONDITION_REQUIRED)
        self.assertTrue(response.data['requires_2fa'])

    def test_can_disable_2fa_with_a_displayed_backup_code(self):
        user = make_user('off@example.com')
        codes = self._enable_2fa(user)
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/auth/2fa/disable/', {'password': 'Str0ng-Pass-123!', 'backup_code': codes[1]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)


class RememberMeTests(AuthFlowBase):
    def test_remember_me_extends_refresh_lifetime_and_survives_rotation(self):
        from datetime import timedelta
        from rest_framework_simplejwt.tokens import RefreshToken

        make_user('rm@example.com')
        short = self.client.post('/api/v1/auth/login/', {'email': 'rm@example.com', 'password': 'Str0ng-Pass-123!'}, format='json')
        long = self.client.post('/api/v1/auth/login/', {'email': 'rm@example.com', 'password': 'Str0ng-Pass-123!', 'remember_me': True}, format='json')
        short_lifetime = RefreshToken(short.data['refresh']).payload['exp'] - RefreshToken(short.data['refresh']).payload['iat']
        long_lifetime = RefreshToken(long.data['refresh']).payload['exp'] - RefreshToken(long.data['refresh']).payload['iat']
        self.assertGreater(long_lifetime, short_lifetime)

        rotated = self.client.post('/api/v1/auth/token/refresh/', {'refresh': long.data['refresh']}, format='json')
        self.assertEqual(rotated.status_code, status.HTTP_200_OK, rotated.data)
        rotated_lifetime = RefreshToken(rotated.data['refresh']).payload['exp'] - RefreshToken(rotated.data['refresh']).payload['iat']
        self.assertGreater(rotated_lifetime, timedelta(days=8).total_seconds())


class SessionManagementTests(AuthFlowBase):
    def test_sessions_list_is_routed_and_marks_the_current_session(self):
        make_user('sess@example.com')
        login = self.client.post('/api/v1/auth/login/', {'email': 'sess@example.com', 'password': 'Str0ng-Pass-123!'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.get('/api/v1/auth/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['is_current'])


class FaceFlowTests(AuthFlowBase):
    def test_face_registration_accepts_multipart_json_descriptor_and_password(self):
        user = make_user('face@example.com')
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/auth/face/register/', {
            'descriptor': json.dumps(DESCRIPTOR),
            'quality_score': '0.8',
            'password': 'Str0ng-Pass-123!',
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(FaceProfile.objects.get(user=user).is_verified)

    def test_face_registration_requires_the_password_for_password_accounts(self):
        user = make_user('nopass@example.com')
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/auth/face/register/', {'descriptor': json.dumps(DESCRIPTOR)}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_social_accounts_without_a_password_can_still_enroll_a_face(self):
        user = make_user('social@example.com', role=None)
        user.set_unusable_password()
        user.save()
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/auth/face/register/', {'descriptor': json.dumps(DESCRIPTOR)}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_face_login_works_for_students(self):
        student = make_user('stu@example.com')
        enroll_face(student)
        response = self.client.post('/api/v1/auth/face/verify/', {'descriptor': DESCRIPTOR}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_face_login_is_refused_for_admin_accounts(self):
        admin = make_user('boss@example.com', role='admin')
        enroll_face(admin)
        response = self.client.post('/api/v1/auth/face/verify/', {'descriptor': DESCRIPTOR}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn('access', response.data)

    def test_face_login_is_refused_for_staff_accounts(self):
        staff = make_user('staff@example.com', role='professeur', is_staff=True)
        enroll_face(staff)
        response = self.client.post('/api/v1/auth/face/verify/', {'descriptor': DESCRIPTOR}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OnboardingEnforcementTests(AuthFlowBase):
    def test_default_permission_blocks_users_who_skipped_onboarding(self):
        user = make_user('skip@example.com')  # no face profile yet
        self.client.force_authenticate(user)
        response = self.client.get('/api/v1/notebooks/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # ...but the profile endpoint stays reachable so the UI can finish onboarding
        self.assertEqual(self.client.get('/api/v1/accounts/me/').status_code, status.HTTP_200_OK)
        me = self.client.get('/api/v1/accounts/me/').data
        self.assertTrue(me['needs_onboarding'])
        self.assertTrue(me['has_password'])

    def test_onboarded_users_get_through(self):
        user = make_user('done@example.com')
        enroll_face(user)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get('/api/v1/notebooks/').status_code, status.HTTP_200_OK)


class AdminApiTests(AuthFlowBase):
    def test_admin_created_users_can_log_in_immediately(self):
        admin = make_user('root@example.com', role='admin', is_superuser=True, is_staff=True)
        self.client.force_authenticate(admin)
        response = self.client.post('/api/v1/accounts/admin/users/', {
            'email': 'Created@Example.com', 'username': 'created', 'first_name': 'C', 'last_name': 'U',
            'role': 'professeur', 'is_active': True,
            'password': 'Str0ng-Pass-123!', 'confirm_password': 'Str0ng-Pass-123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.client.force_authenticate(None)
        login = self.client.post('/api/v1/auth/login/', {'email': 'created@example.com', 'password': 'Str0ng-Pass-123!'}, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.data)

    def test_admin_cannot_create_duplicate_email_differing_by_case(self):
        admin = make_user('root2@example.com', role='admin', is_superuser=True, is_staff=True)
        make_user('dup@example.com')
        self.client.force_authenticate(admin)
        response = self.client.post('/api/v1/accounts/admin/users/', {
            'email': 'DUP@example.com', 'username': 'dup2', 'role': 'etudiant',
            'password': 'Str0ng-Pass-123!', 'confirm_password': 'Str0ng-Pass-123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivating_or_locking_a_user_revokes_their_sessions(self):
        admin = make_user('root3@example.com', role='admin', is_superuser=True, is_staff=True)
        victim = make_user('victim@example.com')
        login = self.client.post('/api/v1/auth/login/', {'email': 'victim@example.com', 'password': 'Str0ng-Pass-123!'}, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertTrue(UserSession.objects.filter(user=victim, revoked_at__isnull=True).exists())

        self.client.force_authenticate(admin)
        self.assertEqual(self.client.post(f'/api/v1/accounts/admin/users/{victim.pk}/lock/').status_code, status.HTTP_200_OK)
        self.assertFalse(UserSession.objects.filter(user=victim, revoked_at__isnull=True).exists())

    @override_settings(REQUIRE_ADMIN_2FA=True)
    def test_admin_api_can_require_two_factor(self):
        admin = make_user('root4@example.com', role='admin', is_superuser=True, is_staff=True)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get('/api/v1/accounts/admin/users/').status_code, status.HTTP_403_FORBIDDEN)
        admin.two_factor_enabled = True
        admin.save()
        self.assertEqual(self.client.get('/api/v1/accounts/admin/users/').status_code, status.HTTP_200_OK)

    def test_non_admins_cannot_reach_the_admin_api(self):
        self.client.force_authenticate(make_user('plain@example.com', role='professeur'))
        self.assertEqual(self.client.get('/api/v1/accounts/admin/users/').status_code, status.HTTP_403_FORBIDDEN)


class SocialPasswordTests(AuthFlowBase):
    def test_social_user_can_set_a_first_password_without_a_current_one(self):
        user = make_user('oauth@example.com')
        user.set_unusable_password()
        user.save()
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/accounts/change-password/', {
            'new_password': 'Br4nd-New-Pass-77!', 'confirm_password': 'Br4nd-New-Pass-77!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Br4nd-New-Pass-77!'))

    def test_password_accounts_still_need_the_current_password(self):
        user = make_user('pw@example.com')
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/accounts/change-password/', {
            'new_password': 'Br4nd-New-Pass-77!', 'confirm_password': 'Br4nd-New-Pass-77!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InvalidUuidTokenTests(AuthFlowBase):
    """Malformed UUID tokens must return 400, never a 500."""
    def test_verify_email_with_malformed_uuid(self):
        response = self.client.post('/api/v1/auth/verify-email/', {
            'token': 'not-a-uuid-at-all',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_with_malformed_uuid(self):
        response = self.client.post('/api/v1/auth/password-reset/confirm/', {
            'token': 'not-a-uuid-at-all',
            'password': 'NewPass123!@',
            'confirm_password': 'NewPass123!@',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FaceLockoutTests(AuthFlowBase):
    """Face-login lockout mirrors password lockout: N failed attempts lock face sign-in."""
    DESCRIPTOR = [0.01 * (i % 7) for i in range(128)]

    def _enroll(self, user, descriptor=None):
        return FaceProfile.objects.create(
            user=user,
            descriptor=descriptor or self.DESCRIPTOR,
            is_verified=True,
        )

    def test_face_locked_user_cannot_face_login(self):
        user = make_user('facelock@example.com', email_verified=True)
        self._enroll(user)
        # Manually place the account in face lockout (as record_failed_face_login would).
        user.face_locked_until = timezone.now() + timezone.timedelta(minutes=30)
        user.save(update_fields=['face_locked_until'])
        response = self.client.post('/api/v1/auth/face/verify/', {
            'descriptor': self.DESCRIPTOR,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('locked', response.data['detail'].lower())

    def test_record_failed_face_login_locks_after_threshold(self):
        from django.utils import timezone
        user = make_user('facelock2@example.com', email_verified=True)
        for _ in range(MAX_FAILED_FACE_ATTEMPTS):
            user.record_failed_face_login()
        user.refresh_from_db()
        self.assertTrue(user.is_face_locked())
        self.assertIsNotNone(user.face_locked_until)

    def test_record_successful_face_login_resets_lockout(self):
        from django.utils import timezone
        user = make_user('facelock3@example.com', email_verified=True)
        user.failed_face_attempts = MAX_FAILED_FACE_ATTEMPTS
        user.face_locked_until = timezone.now() + timezone.timedelta(minutes=30)
        user.save()
        user.record_successful_face_login()
        user.refresh_from_db()
        self.assertEqual(user.failed_face_attempts, 0)
        self.assertIsNone(user.face_locked_until)
        self.assertFalse(user.is_face_locked())


class FaceStepUpTests(AuthFlowBase):
    """A face-authenticated session must step up with a password for sensitive ops."""
    DESCRIPTOR = [0.01 * (i % 7) for i in range(128)]

    def _face_login(self, user):
        self._enroll(user)
        response = self.client.post('/api/v1/auth/face/verify/', {
            'descriptor': self.DESCRIPTOR,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        return response.data

    def _enroll(self, user):
        return FaceProfile.objects.create(
            user=user, descriptor=self.DESCRIPTOR, is_verified=True,
        )

    def test_face_session_cannot_change_password(self):
        user = make_user('stepuppw@example.com', email_verified=True)
        self._face_login(user)
        response = self.client.post('/api/v1/accounts/change-password/', {
            'current_password': 'Str0ng-Pass-123!',
            'new_password': 'NewSecurePass456!@',
            'confirm_password': 'NewSecurePass456!@',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data.get('requires_step_up'))

    def test_face_session_cannot_request_email_change(self):
        user = make_user('stepuemail@example.com', email_verified=True)
        self._face_login(user)
        response = self.client.post('/api/v1/auth/email-change/', {
            'new_email': 'new@example.com',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data.get('requires_step_up'))

    def test_face_session_cannot_request_deletion(self):
        user = make_user('stepupdel@example.com', email_verified=True)
        self._face_login(user)
        response = self.client.post('/api/v1/auth/deletion-request/', {
            'reason': 'testing',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data.get('requires_step_up'))

    def test_password_session_can_perform_sensitive_ops(self):
        user = make_user('stepuppass@example.com', email_verified=True)
        self.client.post('/api/v1/auth/login/', {
            'email': 'stepuppass@example.com', 'password': 'Str0ng-Pass-123!',
        }, format='json')
        # Login uses the test client's sessionless JWT; force_authenticate for the
        # sensitive-op calls so we exercise the password (non-face) path.
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/accounts/change-password/', {
            'current_password': 'Str0ng-Pass-123!',
            'new_password': 'NewSecurePass456!@',
            'confirm_password': 'NewSecurePass456!@',
        }, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
