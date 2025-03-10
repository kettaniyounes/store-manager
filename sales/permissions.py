from rest_framework import permissions


class IsManagerOrReadOnly(permissions.BasePermission):
    
    """
    Allows managers to perform any action, but read-only for others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS: # SAFE_METHODS are GET, HEAD, OPTIONS (read-only)
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']


class IsSalesStaffOrReadOnly(permissions.BasePermission):

    """
    Allows sales staff, managers, and owners to create and manage sales, read-only for others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS: # Allow POST for creating sales
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager', 'staff'] # Allow sales staff to create/manage

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager', 'staff'] # Allow sales staff to view/update/delete their sales (or all sales - depending on requirement)


class IsManagerOrOwnerSale(permissions.BasePermission): # Example permission for more restricted actions on sales (e.g., deleting)

    """
    Allows only managers and owners to perform certain actions on sales (e.g., delete).
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']