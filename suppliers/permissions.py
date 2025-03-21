
# Django Import
from rest_framework import permissions

# Paython Import


class IsManagerOrReadOnlySupplier(permissions.BasePermission):
    """
    Allows managers and owners to perform any action on Suppliers and SupplierProducts,
    but read-only access for other users.
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated and request.method in permissions.SAFE_METHODS: # SAFE_METHODS: GET, HEAD, OPTIONS
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']


class IsPurchasingManagerOrStaffOrCreatePO(permissions.BasePermission):
    """
    Allows Purchasing Managers and Owners to manage Purchase Orders.
    Sales staff can create Purchase Orders, but only read existing ones.
    Read-only for others.
    """
    def has_permission(self, request, view):
        if request.method == 'POST': # Allow POST for creating POs for staff, managers, owners
            return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager', 'staff']
        elif request.user.is_authenticated and request.method in permissions.SAFE_METHODS: # Read-only for safe methods
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager'] # Full access for managers and owners

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS: # Read-only for safe methods
            return True
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager'] # Full access for managers and owners


class IsManagerOrOwnerSupplier(permissions.BasePermission):
    """
    Allows only managers and owners to perform certain actions on Suppliers and SupplierProducts (e.g., delete).
    More restrictive than IsManagerOrReadOnlySupplier.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.profile.role in ['owner', 'manager']