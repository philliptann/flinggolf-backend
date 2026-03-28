from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticatedUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and hasattr(user, "profile")
            and user.profile.is_platform_admin
        )


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
