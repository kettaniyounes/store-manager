import hashlib
import hmac
import time
import secrets
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
import structlog
import re
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)


class SecurityValidator:
    """Comprehensive security validation utilities"""
    
    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\bOR\s+\w+\s*=\s*\w+)",
        r"(\';|\"\;)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
    ]
    
    @classmethod
    def validate_input(cls, data: Any) -> Dict[str, Any]:
        """Validate input data for security threats"""
        threats_found = []
        
        if isinstance(data, str):
            # Check for SQL injection
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, data, re.IGNORECASE):
                    threats_found.append("sql_injection")
                    break
            
            # Check for XSS
            for pattern in cls.XSS_PATTERNS:
                if re.search(pattern, data, re.IGNORECASE):
                    threats_found.append("xss")
                    break
        
        elif isinstance(data, dict):
            for key, value in data.items():
                nested_threats = cls.validate_input(value)
                threats_found.extend(nested_threats.get('threats', []))
        
        elif isinstance(data, list):
            for item in data:
                nested_threats = cls.validate_input(item)
                threats_found.extend(nested_threats.get('threats', []))
        
        return {
            'is_safe': len(threats_found) == 0,
            'threats': list(set(threats_found))
        }
    
    @classmethod
    def sanitize_input(cls, data: str) -> str:
        """Sanitize input data"""
        if not isinstance(data, str):
            return data
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';]', '', data)
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()


class RateLimiter:
    """Advanced rate limiting with different strategies"""
    
    @staticmethod
    def is_rate_limited(identifier: str, limit: int, window: int, prefix: str = "rate_limit") -> bool:
        """Check if identifier is rate limited"""
        cache_key = f"{prefix}_{identifier}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window)
        return False
    
    @staticmethod
    def get_rate_limit_info(identifier: str, prefix: str = "rate_limit") -> Dict[str, Any]:
        """Get rate limit information"""
        cache_key = f"{prefix}_{identifier}"
        current_count = cache.get(cache_key, 0)
        ttl = cache.ttl(cache_key) if hasattr(cache, 'ttl') else None
        
        return {
            'current_count': current_count,
            'time_remaining': ttl,
            'is_limited': current_count > 0
        }


class SecurityAuditor:
    """Security audit and monitoring"""
    
    @staticmethod
    def log_security_event(event_type: str, user_id: Optional[int], ip_address: str, 
                          details: Dict[str, Any], severity: str = "INFO"):
        """Log security events for audit trail"""
        logger.bind(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
            **details
        ).info("security_event")
    
    @staticmethod
    def detect_suspicious_activity(user_id: int, ip_address: str, action: str) -> bool:
        """Detect suspicious user activity patterns"""
        cache_key = f"user_activity_{user_id}_{ip_address}"
        
        # Get recent activity
        recent_activity = cache.get(cache_key, [])
        current_time = time.time()
        
        # Add current action
        recent_activity.append({
            'action': action,
            'timestamp': current_time
        })
        
        # Keep only last 10 minutes of activity
        recent_activity = [
            activity for activity in recent_activity 
            if current_time - activity['timestamp'] < 600
        ]
        
        # Check for suspicious patterns
        if len(recent_activity) > 50:  # Too many actions in 10 minutes
            SecurityAuditor.log_security_event(
                "suspicious_activity_high_frequency",
                user_id,
                ip_address,
                {"action_count": len(recent_activity), "action": action},
                "WARNING"
            )
            return True
        
        # Check for rapid repeated actions
        same_actions = [a for a in recent_activity if a['action'] == action]
        if len(same_actions) > 20:  # Same action repeated too many times
            SecurityAuditor.log_security_event(
                "suspicious_activity_repeated_action",
                user_id,
                ip_address,
                {"repeated_action": action, "count": len(same_actions)},
                "WARNING"
            )
            return True
        
        # Update cache
        cache.set(cache_key, recent_activity, 600)
        return False


def generate_api_key() -> str:
    """Generate secure API key"""
    return secrets.token_urlsafe(32)


def verify_api_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify API request signature"""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)