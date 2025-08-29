from rest_framework import permissions


class IsAnalyticsManagerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for analytics management.
    Allows read access to authenticated users, write access to managers.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.groups.filter(name='Analytics Managers').exists())
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Dashboard owners can edit their own dashboards
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        
        return (
            request.user.is_staff or 
            request.user.groups.filter(name='Analytics Managers').exists()
        )


class IsDashboardOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for dashboard access.
    Dashboard owners can edit, others can only read public dashboards.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions for public dashboards or owned dashboards
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.owner == request.user
        
        # Write permissions only for dashboard owner
        return obj.owner == request.user