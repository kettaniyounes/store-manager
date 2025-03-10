from rest_framework import permissions

class IsSalesOrManagerOrReadOnly(permissions.BasePermission): # Renamed and broadened permission
    
    """
    Allows sales staff, managers, and owners to manage customers, read-only for others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS or request.method == 'POST': # Allow POST for creating customers
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager'] # Allow sales staff to create/manage

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager'] # Allow sales staff to view/update/delete customers