"""
Utility functions for tenant operations.
"""

from django.db import connection
from django_tenants.utils import get_tenant_model, get_public_schema_name, schema_context
from .models import Tenant, TenantUser
import logging

logger = logging.getLogger(__name__)


def get_current_tenant():
    """Get the current tenant from database connection."""
    return getattr(connection, 'tenant', None)


def is_public_schema():
    """Check if current schema is public schema."""
    tenant = get_current_tenant()
    return not tenant or tenant.schema_name == get_public_schema_name()


def get_tenant_by_domain(domain):
    """Get tenant by domain name."""
    from .models import Domain
    try:
        domain_obj = Domain.objects.get(domain=domain)
        return domain_obj.tenant
    except Domain.DoesNotExist:
        return None


def get_user_tenants(user):
    """Get all tenants where user is a member."""
    if not user or not user.is_authenticated:
        return Tenant.objects.none()
    
    tenant_ids = TenantUser.objects.filter(
        user=user, is_active=True
    ).values_list('tenant_id', flat=True)
    
    return Tenant.objects.filter(id__in=tenant_ids, is_active=True)


def switch_tenant_context(tenant_slug):
    """Context manager to switch to specific tenant schema."""
    try:
        tenant = Tenant.objects.get(slug=tenant_slug, is_active=True)
        return schema_context(tenant.schema_name)
    except Tenant.DoesNotExist:
        raise ValueError(f"Tenant with slug '{tenant_slug}' not found")


def create_tenant_user(user, tenant, role='staff', **permissions):
    """Create tenant-user relationship with specified permissions."""
    defaults = {
        'role': role,
        'can_manage_users': permissions.get('can_manage_users', False),
        'can_manage_settings': permissions.get('can_manage_settings', False),
        'can_view_analytics': permissions.get('can_view_analytics', True),
        'can_manage_inventory': permissions.get('can_manage_inventory', False),
        'can_process_sales': permissions.get('can_process_sales', True),
    }
    
    tenant_user, created = TenantUser.objects.get_or_create(
        user=user,
        tenant=tenant,
        defaults=defaults
    )
    
    if not created:
        # Update existing relationship
        for key, value in defaults.items():
            setattr(tenant_user, key, value)
        tenant_user.save()
    
    return tenant_user


def get_tenant_stats(tenant):
    """Get statistics for a tenant."""
    with schema_context(tenant.schema_name):
        from products.models import Product
        from sales.models import Sale
        from customers.models import Customer
        
        stats = {
            'products_count': Product.objects.count(),
            'sales_count': Sale.objects.count(),
            'customers_count': Customer.objects.count(),
            'users_count': TenantUser.objects.filter(tenant=tenant, is_active=True).count(),
        }
        
        return stats


def validate_tenant_access(user, tenant):
    """Validate if user has access to tenant."""
    if not user or not user.is_authenticated:
        return False
    
    try:
        tenant_user = TenantUser.objects.get(
            user=user,
            tenant=tenant,
            is_active=True
        )
        return True
    except TenantUser.DoesNotExist:
        return False


def log_tenant_activity(tenant, user, action, details=None):
    """Log tenant activity for audit purposes."""
    logger.info(
        f"Tenant Activity - Tenant: {tenant.name} ({tenant.schema_name}), "
        f"User: {user.username if user else 'System'}, "
        f"Action: {action}, "
        f"Details: {details or 'N/A'}"
    )


class TenantContext:
    """Context manager for tenant operations."""
    
    def __init__(self, tenant):
        self.tenant = tenant
        self.original_tenant = None
    
    def __enter__(self):
        self.original_tenant = getattr(connection, 'tenant', None)
        connection.set_tenant(self.tenant)
        return self.tenant
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_tenant:
            connection.set_tenant(self.original_tenant)
        else:
            # Reset to public schema
            connection.set_schema_to_public()