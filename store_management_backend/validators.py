from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re


class SecurePasswordValidator:
    """
    Enhanced password validator with comprehensive security checks
    """
    
    def validate(self, password, user=None):
        errors = []
        
        # Minimum length
        if len(password) < 12:
            errors.append("Password must be at least 12 characters long.")
        
        # Must contain uppercase letter
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter.")
        
        # Must contain lowercase letter
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter.")
        
        # Must contain digit
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit.")
        
        # Must contain special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character.")
        
        # Check for common patterns
        if re.search(r'(.)\1{2,}', password):
            errors.append("Password cannot contain repeated characters.")
        
        # Check for sequential characters
        if self.has_sequential_chars(password):
            errors.append("Password cannot contain sequential characters.")
        
        # Check against user information
        if user:
            user_info = [
                getattr(user, 'username', ''),
                getattr(user, 'first_name', ''),
                getattr(user, 'last_name', ''),
                getattr(user, 'email', '').split('@')[0]
            ]
            
            for info in user_info:
                if info and len(info) > 2 and info.lower() in password.lower():
                    errors.append("Password cannot contain personal information.")
                    break
        
        if errors:
            raise ValidationError(errors)
    
    def has_sequential_chars(self, password):
        """Check for sequential characters like 123 or abc"""
        for i in range(len(password) - 2):
            if (ord(password[i]) + 1 == ord(password[i + 1]) and 
                ord(password[i + 1]) + 1 == ord(password[i + 2])):
                return True
        return False
    
    def get_help_text(self):
        return (
            "Your password must be at least 12 characters long, contain uppercase "
            "and lowercase letters, digits, special characters, and cannot contain "
            "repeated or sequential characters or personal information."
        )


class SecureUsernameValidator(RegexValidator):
    """
    Secure username validator
    """
    regex = r'^[a-zA-Z0-9_.-]+$'
    message = 'Username can only contain letters, numbers, underscores, dots, and hyphens.'
    
    def __call__(self, value):
        super().__call__(value)
        
        # Additional checks
        if len(value) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        
        if len(value) > 30:
            raise ValidationError("Username cannot be longer than 30 characters.")
        
        # Check for reserved usernames
        reserved_usernames = [
            'admin', 'administrator', 'root', 'system', 'api', 'www',
            'mail', 'email', 'support', 'help', 'info', 'contact'
        ]
        
        if value.lower() in reserved_usernames:
            raise ValidationError("This username is reserved and cannot be used.")


class SecureEmailValidator:
    """
    Enhanced email validator with security checks
    """
    
    def __call__(self, value):
        # Basic email format validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise ValidationError("Enter a valid email address.")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'[<>"\']',  # HTML/script injection attempts
            r'javascript:',  # JavaScript injection
            r'data:',  # Data URI scheme
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError("Email contains invalid characters.")
        
        # Check domain length
        domain = value.split('@')[1]
        if len(domain) > 253:
            raise ValidationError("Email domain is too long.")
        
        # Check for disposable email domains (basic check)
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email'
        ]
        
        if domain.lower() in disposable_domains:
            raise ValidationError("Disposable email addresses are not allowed.")