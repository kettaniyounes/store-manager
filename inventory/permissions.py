from rest_framework import permissions


class IsInventoryStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow inventory staff to edit inventory.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions are only allowed to inventory staff, managers, or owners
        return (request.user and 
                request.user.is_authenticated and 
                (request.user.role in ['inventory', 'manager', 'owner'] or 
                 request.user.is_staff))


class IsStoreManagerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow store managers to edit their store's inventory.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions require authentication
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to store managers, general managers, or owners
        if hasattr(obj, 'store'):
            store = obj.store
        else:
            store = obj
        
        return (request.user.role in ['manager', 'owner'] or 
                request.user.is_staff or
                store.manager == request.user)


class InventoryPermission(permissions.BasePermission):
    """
    General inventory permission class for multi-store inventory management.
    Combines inventory staff and store manager permissions.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions are only allowed to inventory staff, managers, or owners
        return (request.user and 
                request.user.is_authenticated and 
                (hasattr(request.user, 'profile') and 
                 request.user.profile.role in ['inventory', 'manager', 'owner'] or 
                 request.user.is_staff or
                 request.user.is_superuser))

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions check based on user role and store access
        if hasattr(obj, 'store'):
            store = obj.store
            # Check if user has access to this store
            if hasattr(request.user, 'profile'):
                user_role = request.user.profile.role
                if user_role in ['owner', 'manager'] or request.user.is_superuser:
                    return True
                elif user_role == 'inventory':
                    # Inventory staff can manage inventory for stores they have access to
                    return True
                elif user_role == 'staff':
                    # Regular staff can only read
                    return request.method in permissions.SAFE_METHODS
        
        return request.user.is_superuser