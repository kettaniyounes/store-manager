import time
import json
import structlog
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from django.db import connection
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt
import threading

logger = structlog.get_logger(__name__)

# Thread-local storage for tenant context
_thread_locals = threading.local()


class TenantResolutionMiddleware(MiddlewareMixin):
    """Middleware for resolving tenant context and setting database schema"""
    
    def process_request(self, request):
        """Resolve tenant from request and set database schema"""
        try:
            # Clear any existing tenant context
            self.clear_tenant_context()
            
            # Try to resolve tenant using multiple methods
            tenant = self.resolve_tenant(request)
            
            if tenant:
                # Validate tenant is active
                if tenant.status != 'active':
                    return JsonResponse({
                        'error': 'Tenant not active',
                        'detail': f'Tenant "{tenant.name}" is currently {tenant.status}'
                    }, status=403)
                
                # Set tenant context
                self.set_tenant_context(request, tenant)
                
                # Set database schema
                self.set_database_schema(tenant.schema_name)
                
                logger.info(
                    "tenant_resolved",
                    tenant_name=tenant.name,
                    tenant_slug=tenant.slug,
                    schema_name=tenant.schema_name,
                    resolution_method=getattr(request, '_tenant_resolution_method', 'unknown')
                )
            else:
                # No tenant resolved - use public schema for system endpoints
                if self.is_system_endpoint(request.path):
                    self.set_database_schema('public')
                else:
                    return JsonResponse({
                        'error': 'Tenant not found',
                        'detail': 'Unable to resolve tenant from request'
                    }, status=400)
        
        except Exception as e:
            logger.error(
                "tenant_resolution_error",
                error=str(e),
                path=request.path,
                method=request.method
            )
            return JsonResponse({
                'error': 'Tenant resolution failed',
                'detail': 'Internal error during tenant resolution'
            }, status=500)
    
    def process_response(self, request, response):
        """Clean up tenant context after request"""
        try:
            # Reset database schema to public
            self.set_database_schema('public')
            
            # Clear tenant context
            self.clear_tenant_context()
            
        except Exception as e:
            logger.error("tenant_cleanup_error", error=str(e))
        
        return response
    
    def resolve_tenant(self, request):
        """Resolve tenant using multiple identification methods"""
        from settings_app.models import TenantOrganization
        
        # Method 1: Subdomain-based resolution
        tenant = self.resolve_by_subdomain(request)
        if tenant:
            request._tenant_resolution_method = 'subdomain'
            return tenant
        
        # Method 2: Custom domain resolution
        tenant = self.resolve_by_domain(request)
        if tenant:
            request._tenant_resolution_method = 'domain'
            return tenant
        
        # Method 3: Header-based resolution
        tenant = self.resolve_by_header(request)
        if tenant:
            request._tenant_resolution_method = 'header'
            return tenant
        
        # Method 4: JWT token claims
        tenant = self.resolve_by_jwt_token(request)
        if tenant:
            request._tenant_resolution_method = 'jwt'
            return tenant
        
        # Method 5: API key prefix
        tenant = self.resolve_by_api_key(request)
        if tenant:
            request._tenant_resolution_method = 'api_key'
            return tenant
        
        return None
    
    def resolve_by_subdomain(self, request):
        """Resolve tenant by subdomain (e.g., tenant1.yourdomain.com)"""
        from settings_app.models import TenantOrganization
        
        try:
            host = request.get_host().lower()
            
            # Skip localhost and IP addresses
            if 'localhost' in host or host.replace('.', '').replace(':', '').isdigit():
                return None
            
            # Extract subdomain
            parts = host.split('.')
            if len(parts) >= 3:  # subdomain.domain.com
                subdomain = parts[0]
                
                # Try to find tenant by slug
                try:
                    return TenantOrganization.objects.get(slug=subdomain, status='active')
                except TenantOrganization.DoesNotExist:
                    pass
        
        except Exception as e:
            logger.error("subdomain_resolution_error", error=str(e), host=request.get_host())
        
        return None
    
    def resolve_by_domain(self, request):
        """Resolve tenant by custom domain"""
        from settings_app.models import TenantOrganization
        
        try:
            host = request.get_host().lower()
            
            # Try to find tenant by custom domain
            try:
                return TenantOrganization.objects.get(domain=host, status='active')
            except TenantOrganization.DoesNotExist:
                pass
        
        except Exception as e:
            logger.error("domain_resolution_error", error=str(e), host=request.get_host())
        
        return None
    
    def resolve_by_header(self, request):
        """Resolve tenant by X-Tenant-ID header"""
        from settings_app.models import TenantOrganization
        
        try:
            tenant_id = request.META.get('HTTP_X_TENANT_ID')
            if tenant_id:
                # Try by slug first, then by ID
                try:
                    return TenantOrganization.objects.get(slug=tenant_id, status='active')
                except TenantOrganization.DoesNotExist:
                    try:
                        return TenantOrganization.objects.get(id=tenant_id, status='active')
                    except (TenantOrganization.DoesNotExist, ValueError):
                        pass
        
        except Exception as e:
            logger.error("header_resolution_error", error=str(e))
        
        return None
    
    def resolve_by_jwt_token(self, request):
        """Resolve tenant from JWT token claims"""
        from settings_app.models import TenantOrganization
        
        try:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                
                try:
                    # Decode token without verification for tenant extraction
                    decoded_token = jwt.decode(token, options={"verify_signature": False})
                    tenant_slug = decoded_token.get('tenant_slug') or decoded_token.get('tenant_id')
                    
                    if tenant_slug:
                        try:
                            return TenantOrganization.objects.get(slug=tenant_slug, status='active')
                        except TenantOrganization.DoesNotExist:
                            pass
                
                except jwt.DecodeError:
                    pass
        
        except Exception as e:
            logger.error("jwt_resolution_error", error=str(e))
        
        return None
    
    def resolve_by_api_key(self, request):
        """Resolve tenant by API key prefix (tenant_slug_api_key)"""
        from settings_app.models import TenantOrganization
        
        try:
            api_key = request.META.get('HTTP_X_API_KEY')
            if api_key and '_' in api_key:
                # Extract tenant slug from API key prefix
                tenant_slug = api_key.split('_')[0]
                
                try:
                    return TenantOrganization.objects.get(slug=tenant_slug, status='active')
                except TenantOrganization.DoesNotExist:
                    pass
        
        except Exception as e:
            logger.error("api_key_resolution_error", error=str(e))
        
        return None
    
    def set_tenant_context(self, request, tenant):
        """Set tenant context in request and thread-local storage"""
        request.tenant = tenant
        _thread_locals.tenant = tenant
        _thread_locals.tenant_slug = tenant.slug
        _thread_locals.schema_name = tenant.schema_name
    
    def clear_tenant_context(self):
        """Clear tenant context from thread-local storage"""
        _thread_locals.tenant = None
        _thread_locals.tenant_slug = None
        _thread_locals.schema_name = None
    
    def set_database_schema(self, schema_name):
        """Set PostgreSQL search path to tenant schema"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path = "{schema_name}", public')
        except Exception as e:
            logger.error("schema_set_error", schema=schema_name, error=str(e))
            raise
    
    def is_system_endpoint(self, path):
        """Check if path is a system endpoint that doesn't require tenant resolution"""
        system_paths = [
            '/admin/',
            '/api/v1/users/register/',
            '/api/v1/users/login/',
            '/swagger/',
            '/redoc/',
            '/static/',
            '/media/',
        ]
        
        return any(path.startswith(system_path) for system_path in system_paths)


def get_current_tenant():
    """Get current tenant from thread-local storage"""
    return getattr(_thread_locals, 'tenant', None)


def get_current_tenant_slug():
    """Get current tenant slug from thread-local storage"""
    return getattr(_thread_locals, 'tenant_slug', None)


def get_current_schema_name():
    """Get current schema name from thread-local storage"""
    return getattr(_thread_locals, 'schema_name', None)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware for comprehensive request/response logging"""
    
    def process_request(self, request):
        request.start_time = time.time()
        
        # Get tenant info for logging
        tenant_info = {}
        if hasattr(request, 'tenant'):
            tenant_info = {
                'tenant_name': request.tenant.name,
                'tenant_slug': request.tenant.slug,
                'schema_name': request.tenant.schema_name
            }
        
        # Log incoming request
        logger.info(
            "incoming_request",
            method=request.method,
            path=request.path,
            user=str(request.user) if hasattr(request, 'user') else 'Anonymous',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            **tenant_info
        )
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Get tenant info for logging
            tenant_info = {}
            if hasattr(request, 'tenant'):
                tenant_info = {
                    'tenant_name': request.tenant.name,
                    'tenant_slug': request.tenant.slug
                }
            
            # Log response
            logger.info(
                "outgoing_response",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                user=str(request.user) if hasattr(request, 'user') else 'Anonymous',
                **tenant_info
            )
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware to add security headers"""
    
    def process_response(self, request, response):
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Custom rate limiting middleware for additional protection"""
    
    def process_request(self, request):
        if request.path.startswith('/api/'):
            client_ip = self.get_client_ip(request)
            cache_key = f"rate_limit_{client_ip}"
            
            # Get current request count
            current_requests = cache.get(cache_key, 0)
            
            # Check if limit exceeded
            if current_requests >= 1000:  # 1000 requests per hour
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'detail': 'Too many requests. Please try again later.'
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, current_requests + 1, 3600)  # 1 hour timeout
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip