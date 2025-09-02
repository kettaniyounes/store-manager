from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .context import TenantContextManager
from .base_models import TenantAwareHistoricalModel, SharedReferenceModel
from .base_serializers import TenantAwareModelSerializer


class TenantAwareModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that automatically handles tenant filtering and context
    """
    
    def get_queryset(self):
        """Filter queryset by current tenant"""
        queryset = super().get_queryset()
        
        # Only filter if the model is tenant-aware
        if hasattr(self.queryset.model, '_tenant_field'):
            current_tenant = TenantContextManager.get_current_tenant()
            if current_tenant:
                tenant_field = self.queryset.model._tenant_field
                queryset = queryset.filter(**{tenant_field: current_tenant})
        
        return queryset
    
    def perform_create(self, serializer):
        """Ensure created objects are associated with current tenant"""
        current_tenant = TenantContextManager.get_current_tenant()
        
        # Set tenant context if model is tenant-aware
        if current_tenant and hasattr(self.queryset.model, '_tenant_field'):
            tenant_field = self.queryset.model._tenant_field
            if tenant_field not in serializer.validated_data:
                serializer.save(**{tenant_field: current_tenant})
            else:
                serializer.save()
        else:
            serializer.save()
    
    def perform_update(self, serializer):
        """Ensure updated objects maintain tenant association"""
        current_tenant = TenantContextManager.get_current_tenant()
        
        # Validate tenant ownership before update
        if current_tenant and hasattr(self.queryset.model, '_tenant_field'):
            instance = serializer.instance
            tenant_field = self.queryset.model._tenant_field
            if getattr(instance, tenant_field, None) != current_tenant:
                raise permissions.PermissionDenied("Cannot modify objects from other tenants")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Ensure only tenant-owned objects can be deleted"""
        current_tenant = TenantContextManager.get_current_tenant()
        
        # Validate tenant ownership before deletion
        if current_tenant and hasattr(self.queryset.model, '_tenant_field'):
            tenant_field = self.queryset.model._tenant_field
            if getattr(instance, tenant_field, None) != current_tenant:
                raise permissions.PermissionDenied("Cannot delete objects from other tenants")
        
        super().perform_destroy(instance)


class SharedReferenceModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for shared reference models (global across tenants)
    """
    
    def get_permissions(self):
        """
        Shared reference models typically have more restrictive permissions
        Only allow read access by default, write access for managers
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
        
        return [permission() for permission in permission_classes]


class TenantAwarePermission(permissions.BasePermission):
    """
    Custom permission class that ensures tenant isolation
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access the view"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Ensure tenant context is available
        current_tenant = TenantContextManager.get_current_tenant()
        if not current_tenant:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific object"""
        current_tenant = TenantContextManager.get_current_tenant()
        
        # For tenant-aware models, check tenant ownership
        if hasattr(obj._meta.model, '_tenant_field'):
            tenant_field = obj._meta.model._tenant_field
            return getattr(obj, tenant_field, None) == current_tenant
        
        # For shared reference models, allow access
        return True


class TenantAwareReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet with tenant filtering
    """
    
    def get_queryset(self):
        """Filter queryset by current tenant"""
        queryset = super().get_queryset()
        
        # Only filter if the model is tenant-aware
        if hasattr(self.queryset.model, '_tenant_field'):
            current_tenant = TenantContextManager.get_current_tenant()
            if current_tenant:
                tenant_field = self.queryset.model._tenant_field
                queryset = queryset.filter(**{tenant_field: current_tenant})
        
        return queryset