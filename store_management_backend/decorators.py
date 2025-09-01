from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from .security import SecurityValidator, RateLimiter, SecurityAuditor
import structlog

logger = structlog.get_logger(__name__)


def validate_input_security(view_func):
    """Decorator to validate input for security threats"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get client IP
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                   request.META.get('REMOTE_ADDR', '')
        
        # Validate request data
        if hasattr(request, 'data') and request.data:
            validation_result = SecurityValidator.validate_input(request.data)
            
            if not validation_result['is_safe']:
                SecurityAuditor.log_security_event(
                    "security_threat_detected",
                    getattr(request.user, 'id', None),
                    client_ip,
                    {
                        "threats": validation_result['threats'],
                        "endpoint": request.path,
                        "method": request.method
                    },
                    "CRITICAL"
                )
                
                return JsonResponse({
                    'error': 'Invalid input detected',
                    'code': 'SECURITY_VIOLATION'
                }, status=400)
        
        return view_func(request, *args, **kwargs)
    return wrapper


def rate_limit(limit: int, window: int, per: str = 'ip'):
    """Advanced rate limiting decorator"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Determine identifier based on 'per' parameter
            if per == 'ip':
                identifier = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                           request.META.get('REMOTE_ADDR', '')
            elif per == 'user' and hasattr(request, 'user') and request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            else:
                identifier = 'anonymous'
            
            # Check rate limit
            if RateLimiter.is_rate_limited(identifier, limit, window, f"custom_{view_func.__name__}"):
                SecurityAuditor.log_security_event(
                    "rate_limit_exceeded",
                    getattr(request.user, 'id', None),
                    identifier,
                    {
                        "endpoint": request.path,
                        "limit": limit,
                        "window": window
                    },
                    "WARNING"
                )
                
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT_EXCEEDED'
                }, status=429)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def monitor_suspicious_activity(view_func):
    """Monitor for suspicious user activity"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if hasattr(request, 'user') and request.user.is_authenticated:
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                       request.META.get('REMOTE_ADDR', '')
            
            action = f"{request.method}_{request.path}"
            
            if SecurityAuditor.detect_suspicious_activity(request.user.id, client_ip, action):
                # Log but don't block - just monitor
                logger.warning(
                    "suspicious_activity_detected",
                    user_id=request.user.id,
                    ip_address=client_ip,
                    action=action
                )
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_api_key(view_func):
    """Require valid API key for access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
        
        if not api_key:
            return JsonResponse({
                'error': 'API key required',
                'code': 'API_KEY_MISSING'
            }, status=401)
        
        # Validate API key (you would implement your own validation logic)
        valid_keys = cache.get('valid_api_keys', [])
        if api_key not in valid_keys:
            SecurityAuditor.log_security_event(
                "invalid_api_key_used",
                None,
                request.META.get('REMOTE_ADDR', ''),
                {"api_key": api_key[:8] + "..."},  # Log partial key for security
                "WARNING"
            )
            
            return JsonResponse({
                'error': 'Invalid API key',
                'code': 'API_KEY_INVALID'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    return wrapper