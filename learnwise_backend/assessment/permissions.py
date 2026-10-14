"""
Permissions du module `assessment`.

Règle du contrat : le professeur crée, relit et publie ; l'étudiant lit
les quiz publiés. Les rôles viennent de `accounts.User.role`.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

# Rôles autorisés à écrire (créer, modifier, publier).
TEACHER_ROLES = ('professeur', 'admin')


def is_teacher(user):
    """True si l'utilisateur est connecté ET a un rôle de professeur/admin."""
    return bool(
        user and user.is_authenticated and getattr(user, 'role', None) in TEACHER_ROLES
    )


def is_admin(user):
    """True si l'utilisateur est connecté avec le rôle admin (voit tous les quiz)."""
    return bool(user and user.is_authenticated and getattr(user, 'role', None) == 'admin')


def is_student(user):
    """True pour un utilisateur connecté qui n'est ni professeur ni admin."""
    return bool(user and user.is_authenticated and not is_teacher(user))


class IsStudent(BasePermission):
    """Réservé aux étudiants : seuls eux passent les quiz (les profs relisent, ne passent pas)."""
    message = 'Only students can take quizzes.'

    def has_permission(self, request, view):
        return is_student(request.user)


class IsTeacher(BasePermission):
    """Réservé aux professeurs/admins (ex : publier un quiz)."""
    message = 'Only teachers can perform this action.'

    def has_permission(self, request, view):
        return is_teacher(request.user)


class IsTeacherOrReadOnly(BasePermission):
    """Lecture pour tout utilisateur connecté ; écriture pour les professeurs/admins."""
    message = 'Only teachers can create or modify quizzes.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return is_teacher(request.user)