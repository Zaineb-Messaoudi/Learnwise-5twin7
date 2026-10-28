from django.conf import settings
from rest_framework import permissions


def is_admin_user(user):
    """Single source of truth for "is this an administrator".

    Django superusers count as admins so `manage.py createsuperuser` stays a
    usable bootstrap path. Do not use DRF's IsAdminUser (it only checks is_staff).
    """
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == 'admin'))


class IsOnboarded(permissions.BasePermission):
    """Authenticated AND finished onboarding (role chosen + face enrolled).

    This is the project-wide default permission, so an account that skipped the
    onboarding screens in the browser still cannot use the API. Endpoints that
    must stay reachable during onboarding (profile, role selection, face
    enrolment, logout, ...) declare ``IsAuthenticated`` explicitly.
    """
    message = 'Please complete your profile (choose a role and register your face) before continuing.'
    code = 'onboarding_required'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return not user.needs_onboarding()


class IsStudent(permissions.BasePermission):
    """Allows access only to users with student role (etudiant)."""
    message = 'Only students can access this resource.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'etudiant')


class IsProfessor(permissions.BasePermission):
    """Allows access only to users with professor role (professeur)."""
    message = 'Only professors can access this resource.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'professeur')


class IsAdmin(permissions.BasePermission):
    """Allows access only to administrators (role 'admin' or Django superuser).

    With REQUIRE_ADMIN_2FA=True (recommended in production) an administrator must also
    have two-factor authentication enabled: sign in, enable 2FA from the security
    settings, then the admin API unlocks. Enrolling 2FA itself never requires IsAdmin.
    """
    message = 'Only administrators can access this resource.'

    def has_permission(self, request, view):
        user = request.user
        if not is_admin_user(user):
            return False
        if getattr(settings, 'REQUIRE_ADMIN_2FA', False) and not user.two_factor_enabled:
            self.message = 'Enable two-factor authentication on your account to use the administration area.'
            return False
        return True


class IsProfessorOrAdmin(permissions.BasePermission):
    """Allows access to professors and administrators."""
    message = 'Only professors and administrators can access this resource.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.role == 'professeur' or is_admin_user(user)))


class IsStudentOrProfessor(permissions.BasePermission):
    """Allows access to students and professors."""
    message = 'Only students and professors can access this resource.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in ('etudiant', 'professeur'))


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allows access to the object owner or an administrator."""
    message = 'You do not have permission to access this resource.'

    def has_object_permission(self, request, view, obj):
        if is_admin_user(request.user):
            return True
        owner = getattr(obj, 'user', None)
        return owner is not None and owner == request.user
