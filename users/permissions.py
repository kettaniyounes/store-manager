from rest_framework import permissions

class IsAdminOrReadOnlyUser(permissions.BasePermission):
    
    """
    Allows admin users to perform any action on users, read-only for others.
    """
    def has_permission(self, request, view):

        return request.user.is_authenticated and request.user.is_staff and request.user.is_superuser # Only superusers for write operations

    def has_object_permission(self, request, view, obj):

        return request.user.is_authenticated and request.user.is_staff and request.user.is_superuser # Only superusers for object-level write operations