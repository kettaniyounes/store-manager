"""
Custom middleware for tenant-aware operations and security.
"""

from django.http import Http404, JsonResponse
from django.db import connection
from django.utils.deprecation import MiddlewareMixin
from django_tenants.middleware import TenantMainMiddleware
from django_tenants.utils import get_tenant_model, get_public_schema_name
from .models import Tenant, TenantUser
import logging

logger = logging.getLogger(__name__)


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware to add tenant context to requests and handle tenant-specific operations.
    """
    
    def process_request(self, request):
        """Add tenant information to request context."""
        tenant = getattr(connection, 'tenant', None)
        
        if tenant and not tenant.schema_name == get_public_schema_name():
            # Add tenant to request for easy access
            request.tenant = tenant
            
            # Add tenant information to request headers for logging
            request.META['HTTP_X_TENANT_ID'] = str(tenant.id)
            request.META['HTTP_X_TENANT_NAME'] = tenant.name
            request.META['HTTP_X_TENANT_SCHEMA'] = tenant.schema_name
            
            # Check if tenant is active
            if not tenant.is_active:
                return JsonResponse(
                    {'error': 'Tenant is not active'}, 
                    status=403
                )
            
            # Check subscription status
            if tenant.subscription_plan == 'trial' and tenant.trial_end_date:
                from django.utils import timezone
                if tenant.trial_end_date < timezone.now():
                    return JsonResponse(
                        {'error': 'Trial period has expired'}, 
                        status=402  # Payment Required
                    )
        else:
            request.tenant = None
        
        return None

    def process_response(self, request, response):
        """Add tenant information to response headers."""
        tenant = getattr(request, 'tenant', None)
        
        if tenant:
            response['X-Tenant-ID'] = str(tenant.id)
            response['X-Tenant-Name'] = tenant.name
            response['X-Tenant-Schema'] = tenant.schema_name
        
        return response


class TenantUserMiddleware(MiddlewareMixin):
    """
    Middleware to add tenant-user relationship context to authenticated requests.
    """
    
    def process_request(self, request):
        """Add tenant user information to request."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            tenant = getattr(request, 'tenant', None)
            
            if tenant:
                try:
                    tenant_user = TenantUser.objects.get(
                        user=request.user,
                        tenant=tenant,
                        is_active=True
                    )
                    request.tenant_user = tenant_user
                    
                    # Add user permissions to request for easy access
                    request.tenant_permissions = {
                        'can_manage_users': tenant_user.can_manage_users,
                        'can_manage_settings': tenant_user.can_manage_settings,
                        'can_view_analytics': tenant_user.can_view_analytics,
                        'can_manage_inventory': tenant_user.can_manage_inventory,
                        'can_process_sales': tenant_user.can_process_sales,
                        'is_owner_or_admin': tenant_user.is_owner_or_admin,
                    }
                    
                except TenantUser.DoesNotExist:
                    # User doesn't belong to this tenant
                    if not request.path.startswith('/api/v1/auth/'):
                        return JsonResponse(
                            {'error': 'User does not have access to this tenant'}, 
                            status=403
                        )
            else:
                request.tenant_user = None
                request.tenant_permissions = {}
        
        return None


class TenantSecurityMiddleware(MiddlewareMixin):
    """
    Security middleware for tenant-specific operations.
    """
    
    def process_request(self, request):
        """Apply tenant-specific security measures."""
        tenant = getattr(request, 'tenant', None)
        
        if tenant:
            # Log tenant access for security monitoring
            logger.info(
                f"Tenant access: {tenant.name} ({tenant.schema_name}) "
                f"from IP: {self.get_client_ip(request)} "
                f"User: {getattr(request.user, 'username', 'Anonymous')}"
            )
            
            # Add tenant-specific rate limiting headers
            request.META['HTTP_X_TENANT_RATE_LIMIT'] = self.get_tenant_rate_limit(tenant)
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_tenant_rate_limit(self, tenant):
        """Get rate limit based on tenant subscription."""
        rate_limits = {
            'trial': '50/minute',
            'basic': '100/minute',
            'premium': '200/minute',
            'enterprise': '500/minute',
        }
        return rate_limits.get(tenant.subscription_plan, '50/minute')