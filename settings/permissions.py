from rest_framework import permissions


class IsOwnerOrManagerReadOnlySetting(permissions.BasePermission):
    
    """
    Allows owners and managers to manage store settings, read-only for others.
    For settings, even listing might be restricted to authenticated users in a real app.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS: # Read-only requests
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager'] # Only owners and managers for write operations

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager'] # Only owners and managers for object-level write operations