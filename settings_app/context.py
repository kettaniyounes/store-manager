from django.db import connection
from .models import TenantOrganization
from .utils import SchemaManager
import threading

# Thread-local storage for tenant context
_thread_locals = threading.local()


class TenantContextManager:
    """Manager for tenant context operations"""
    
    @staticmethod
    def set_tenant_context(tenant):
        """Set tenant context in thread-local storage"""
        _thread_locals.tenant = tenant
        _thread_locals.tenant_slug = tenant.slug if tenant else None
        _thread_locals.schema_name = tenant.schema_name if tenant else None
    
    @staticmethod
    def get_current_tenant():
        """Get current tenant from thread-local storage"""
        return getattr(_thread_locals, 'tenant', None)
    
    @staticmethod
    def get_current_tenant_slug():
        """Get current tenant slug from thread-local storage"""
        return getattr(_thread_locals, 'tenant_slug', None)
    
    @staticmethod
    def get_current_schema_name():
        """Get current schema name from thread-local storage"""
        return getattr(_thread_locals, 'schema_name', None)
    
    @staticmethod
    def clear_tenant_context():
        """Clear tenant context from thread-local storage"""
        _thread_locals.tenant = None
        _thread_locals.tenant_slug = None
        _thread_locals.schema_name = None
    
    @staticmethod
    def require_tenant():
        """Ensure tenant context is set, raise exception if not"""
        tenant = TenantContextManager.get_current_tenant()
        if not tenant:
            raise ValueError("No tenant context available")
        return tenant


class TenantAwareManager:
    """Base manager for tenant-aware model operations"""
    
    def get_queryset(self):
        """Override to ensure tenant context is applied"""
        tenant = TenantContextManager.get_current_tenant()
        if tenant:
            # Schema is already set by middleware, just return normal queryset
            return super().get_queryset()
        else:
            # No tenant context - this might be a system operation
            return super().get_queryset()


def tenant_required(func):
    """Decorator to ensure tenant context is available"""
    def wrapper(*args, **kwargs):
        tenant = TenantContextManager.get_current_tenant()
        if not tenant:
            raise ValueError("Tenant context required for this operation")
        return func(*args, **kwargs)
    return wrapper


def with_tenant_context(tenant_slug):
    """Decorator to execute function with specific tenant context"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Store original context
            original_tenant = TenantContextManager.get_current_tenant()
            
            try:
                # Set new tenant context
                tenant = TenantOrganization.objects.get(slug=tenant_slug)
                TenantContextManager.set_tenant_context(tenant)
                
                # Set database schema
                SchemaManager.set_tenant_schema(tenant_slug)
                
                # Execute function
                result = func(*args, **kwargs)
                
                return result
            
            finally:
                # Restore original context
                if original_tenant:
                    TenantContextManager.set_tenant_context(original_tenant)
                    SchemaManager.set_tenant_schema(original_tenant.slug)
                else:
                    TenantContextManager.clear_tenant_context()
                    SchemaManager.reset_search_path()
        
        return wrapper
    return decorator