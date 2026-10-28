from rest_framework.permissions import SAFE_METHODS, BasePermission
from accounts.permissions import is_admin_user

class AnalyticsRolePermission(BasePermission):
    """Students manage their data; teachers and admins have read-only oversight."""
    message = "Your role does not allow this analytics operation."
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == "etudiant":
            return True
        return request.method in SAFE_METHODS and (user.role == "professeur" or is_admin_user(user))
