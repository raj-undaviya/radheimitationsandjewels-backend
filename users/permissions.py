from rest_framework.permissions import BasePermission

class IsAdminUserRole(BasePermission):

    def has_permission(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.role == "admin"