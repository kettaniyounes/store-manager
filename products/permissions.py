
# Django Import
from rest_framework import permissions

# Python Import



class IsManagerOrReadOnly(permissions.BasePermission):
    """
    Allows managers to perform any action, but read-only for others, just for authenticated user
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated: # SAFE_METHODS are GET, HEAD, OPTIONS (read-only)
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated:
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']

class IsInventoryStaffOrReadOnly(permissions.BasePermission):
    """
    Allows inventory staff to create and update products (especially stock), but read-only for others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS or request.method == 'POST': # Allow POST for creation
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager', 'inventory']

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS or request.method in ['PUT', 'PATCH']: # Allow PUT/PATCH for update
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager', 'inventory']

class IsOwnerOrManager(permissions.BasePermission):
    """
    Allows only owners and managers.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']