import time
import json
import structlog
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware for comprehensive request/response logging"""
    
    def process_request(self, request):
        request.start_time = time.time()
        
        # Log incoming request
        logger.info(
            "incoming_request",
            method=request.method,
            path=request.path,
            user=str(request.user) if hasattr(request, 'user') else 'Anonymous',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log response
            logger.info(
                "outgoing_response",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                user=str(request.user) if hasattr(request, 'user') else 'Anonymous',
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