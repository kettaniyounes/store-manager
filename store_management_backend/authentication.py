from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)
User = get_user_model()


class SecureJWTAuthentication(JWTAuthentication):
    """
    Enhanced JWT authentication with additional security checks
    """
    
    def authenticate(self, request):
        # Get the standard JWT authentication result
        result = super().authenticate(request)
        
        if result is None:
            return None
        
        user, validated_token = result
        
        # Additional security checks
        if not self.is_token_valid(user, validated_token, request):
            raise exceptions.AuthenticationFailed('Token validation failed')
        
        # Log successful authentication
        logger.info(
            "jwt_authentication_success",
            user_id=user.id,
            username=user.username,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            endpoint=request.path
        )
        
        return user, validated_token
    
    def is_token_valid(self, user, token, request):
        """
        Perform additional token validation checks
        """
        # Check if user account is still active
        if not user.is_active:
            logger.warning(
                "inactive_user_token_used",
                user_id=user.id,
                username=user.username
            )
            return False
        
        # Check for token blacklist (if implemented)
        token_jti = token.get('jti')
        if token_jti and cache.get(f"blacklisted_token_{token_jti}"):
            logger.warning(
                "blacklisted_token_used",
                user_id=user.id,
                token_jti=token_jti
            )
            return False
        
        # Check for concurrent session limits
        active_sessions_key = f"active_sessions_{user.id}"
        active_sessions = cache.get(active_sessions_key, set())
        
        # Limit to 5 concurrent sessions per user
        if len(active_sessions) > 5:
            logger.warning(
                "concurrent_session_limit_exceeded",
                user_id=user.id,
                active_sessions_count=len(active_sessions)
            )
            # Remove oldest session
            oldest_session = min(active_sessions)
            active_sessions.remove(oldest_session)
            cache.set(f"blacklisted_token_{oldest_session}", True, 86400)
        
        # Add current session
        active_sessions.add(token_jti)
        cache.set(active_sessions_key, active_sessions, 86400)
        
        # Check for suspicious IP changes
        last_ip_key = f"last_ip_{user.id}"
        current_ip = request.META.get('REMOTE_ADDR', '')
        last_ip = cache.get(last_ip_key)
        
        if last_ip and last_ip != current_ip:
            logger.info(
                "ip_address_changed",
                user_id=user.id,
                old_ip=last_ip,
                new_ip=current_ip
            )
            # Could implement additional verification here
        
        cache.set(last_ip_key, current_ip, 86400)
        
        return True


class APIKeyAuthentication:
    """
    Simple API key authentication for external integrations
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
        
        # Validate API key
        if not self.is_valid_api_key(api_key):
            raise exceptions.AuthenticationFailed('Invalid API key')
        
        # Get associated user (if any)
        user = self.get_user_for_api_key(api_key)
        
        logger.info(
            "api_key_authentication_success",
            api_key_prefix=api_key[:8],
            user_id=getattr(user, 'id', None),
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return user, api_key
    
    def is_valid_api_key(self, api_key):
        """Validate API key against stored keys"""
        valid_keys = cache.get('valid_api_keys', {})
        return api_key in valid_keys
    
    def get_user_for_api_key(self, api_key):
        """Get user associated with API key"""
        api_key_users = cache.get('api_key_users', {})
        user_id = api_key_users.get(api_key)
        
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        
        return None