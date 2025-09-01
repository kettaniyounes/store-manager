from rest_framework import permissions
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import structlog

logger = structlog.get_logger(__name__)


class IsAdminOrReadOnlyUser(permissions.BasePermission):
    """
    Allows admin users to perform any action on users, read-only for others.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff and request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.is_staff and request.user.is_superuser


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must have an attribute named `owner`.
        return obj.owner == request.user


class IsStoreManagerOrReadOnly(permissions.BasePermission):
    """
    Permission for store managers to manage their store's data
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Check if user is a store manager
        return hasattr(request.user, 'profile') and request.user.profile.role in ['manager', 'admin']
    
    def has_object_permission(self, request, view, obj):
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Check if user manages this store
        if hasattr(obj, 'store'):
            user_stores = request.user.profile.managed_stores.all() if hasattr(request.user, 'profile') else []
            return obj.store in user_stores
        
        return False


class RateLimitedPermission(permissions.BasePermission):
    """
    Permission class that implements rate limiting
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check rate limit for this user
        cache_key = f"api_rate_limit_{request.user.id}"
        current_requests = cache.get(cache_key, 0)
        
        # Allow 1000 requests per hour for authenticated users
        if current_requests >= 1000:
            logger.warning(
                "rate_limit_exceeded",
                user_id=request.user.id,
                current_requests=current_requests,
                endpoint=request.path
            )
            return False
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, 3600)
        return True


class TimeBasedPermission(permissions.BasePermission):
    """
    Permission that restricts access based on time windows
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Example: Restrict certain operations to business hours
        current_hour = timezone.now().hour
        
        # Allow admin operations only during business hours (9 AM - 6 PM)
        if hasattr(view, 'admin_only_hours') and view.admin_only_hours:
            if not (9 <= current_hour <= 18):
                if not request.user.is_superuser:
                    return False
        
        return True


class IPWhitelistPermission(permissions.BasePermission):
    """
    Permission that restricts access based on IP whitelist
    """
    def has_permission(self, request, view):
        # Get client IP
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                   request.META.get('REMOTE_ADDR', '')
        
        # Get whitelisted IPs from cache or settings
        whitelisted_ips = cache.get('whitelisted_ips', [])
        
        # If no whitelist is configured, allow all
        if not whitelisted_ips:
            return True
        
        # Check if IP is whitelisted
        if client_ip not in whitelisted_ips:
            logger.warning(
                "ip_not_whitelisted",
                client_ip=client_ip,
                endpoint=request.path,
                user_id=getattr(request.user, 'id', None)
            )
            return False
        
        return True


class SecureAPIPermission(permissions.BasePermission):
    """
    Comprehensive security permission combining multiple checks
    """
    def has_permission(self, request, view):
        # Basic authentication check
        if not request.user.is_authenticated:
            return False
        
        # Check if user account is active and not locked
        if not request.user.is_active:
            return False
        
        # Check for account lockout
        lockout_key = f"account_lockout_{request.user.id}"
        if cache.get(lockout_key):
            logger.warning(
                "locked_account_access_attempt",
                user_id=request.user.id,
                endpoint=request.path
            )
            return False
        
        # Check for suspicious activity
        suspicious_key = f"suspicious_activity_{request.user.id}"
        if cache.get(suspicious_key):
            logger.warning(
                "suspicious_account_access_attempt",
                user_id=request.user.id,
                endpoint=request.path
            )
            # Don't block, but log for monitoring
        
        return True


class AuditPermission(permissions.BasePermission):
    """
    Permission that logs all access attempts for audit purposes
    """
    def has_permission(self, request, view):
        # Log all API access attempts
        logger.info(
            "api_access_attempt",
            user_id=getattr(request.user, 'id', None),
            username=getattr(request.user, 'username', 'anonymous'),
            endpoint=request.path,
            method=request.method,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            timestamp=timezone.now().isoformat()
        )
        
        return True  # This permission only logs, doesn't restrict