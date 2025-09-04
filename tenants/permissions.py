"""
Custom permissions for tenant-aware operations.
"""

from rest_framework import permissions
from .models import TenantUser


class IsTenantMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the current tenant.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False
        
        try:
            tenant_user = TenantUser.objects.get(
                user=request.user,
                tenant=tenant,
                is_active=True
            )
            # Add tenant_user to request for easy access
            request.tenant_user = tenant_user
            return True
        except TenantUser.DoesNotExist:
            return False


class IsTenantOwnerOrAdmin(IsTenantMember):
    """
    Permission to check if user is owner or admin of the current tenant.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant_user = getattr(request, 'tenant_user', None)
        return tenant_user and tenant_user.role in ['owner', 'admin']


class CanManageUsers(IsTenantMember):
    """
    Permission to check if user can manage other users in the tenant.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant_user = getattr(request, 'tenant_user', None)
        return tenant_user and tenant_user.can_manage_users


class CanManageSettings(IsTenantMember):
    """
    Permission to check if user can manage tenant settings.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant_user = getattr(request, 'tenant_user', None)
        return tenant_user and tenant_user.can_manage_settings


class CanViewAnalytics(IsTenantMember):
    """
    Permission to check if user can view analytics.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant_user = getattr(request, 'tenant_user', None)
        return tenant_user and tenant_user.can_view_analytics


class CanManageInventory(IsTenantMember):
    """
    Permission to check if user can manage inventory.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant_user = getattr(request, 'tenant_user', None)
        return tenant_user and tenant_user.can_manage_inventory


class CanProcessSales(IsTenantMember):
    """
    Permission to check if user can process sales.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant_user = getattr(request, 'tenant_user', None)
        return tenant_user and tenant_user.can_process_sales


class IsOwnerOrReadOnly(IsTenantMember):
    """
    Permission to allow owners full access, others read-only.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        tenant_user = getattr(request, 'tenant_user', None)
        if not tenant_user:
            return False
        
        # Owners can do anything
        if tenant_user.role == 'owner':
            return True
        
        # Others can only read
        return request.method in permissions.SAFE_METHODS


class TenantObjectPermission(permissions.BasePermission):
    """
    Base permission for tenant-specific object access.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if object belongs to current tenant
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False
        
        # Check if object has tenant relationship
        if hasattr(obj, 'tenant'):
            return obj.tenant == tenant
        elif hasattr(obj, 'store') and hasattr(obj.store, 'tenant'):
            return obj.store.tenant == tenant
        
        return True