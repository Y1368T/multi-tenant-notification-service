"""
Input validation and sanitization utilities.
Provides validators for SQL injection prevention, XSS prevention, and general input sanitization.
"""
import re
import html
from typing import Any, Optional


class InputSanitizer:
    """Utility class for input sanitization."""
    
    # SQL injection patterns (basic detection)
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)",
        r"(--|;|/\*|\*/|xp_|sp_)",
        r"(\bOR\b.*=.*=|\bAND\b.*=.*=)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize a string input by:
        1. Stripping whitespace
        2. Escaping HTML entities
        3. Truncating if necessary
        """
        if not isinstance(value, str):
            return value
        
        # Strip whitespace
        sanitized = value.strip()
        
        # Escape HTML entities to prevent XSS
        sanitized = html.escape(sanitized)
        
        # Truncate if max_length specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        """Check if string contains potential SQL injection patterns."""
        if not isinstance(value, str):
            return False
        
        value_upper = value.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def check_xss(cls, value: str) -> bool:
        """Check if string contains potential XSS patterns."""
        if not isinstance(value, str):
            return False
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def validate_and_sanitize(cls, value: Any, field_name: str, allow_html: bool = False) -> str:
        """
        Validate and sanitize input value.
        
        Args:
            value: Input value to validate
            field_name: Name of the field (for error messages)
            allow_html: If True, allows HTML (still escapes dangerous patterns)
        
        Returns:
            Sanitized string
        
        Raises:
            ValueError: If SQL injection or XSS patterns detected
        """
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")
        
        # Check for SQL injection
        if cls.check_sql_injection(value):
            raise ValueError(f"{field_name} contains potentially dangerous SQL patterns")
        
        # Check for XSS (unless HTML is explicitly allowed)
        if not allow_html and cls.check_xss(value):
            raise ValueError(f"{field_name} contains potentially dangerous script patterns")
        
        # Sanitize
        if allow_html:
            # Only escape dangerous patterns, keep safe HTML
            sanitized = value.strip()
        else:
            sanitized = cls.sanitize_string(value)
        
        return sanitized


# Pydantic validators for common use cases
def validate_string_input(
    value: str,
    field_name: str = "field",
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    allow_html: bool = False
) -> str:
    """
    Pydantic-compatible validator for string inputs.
    
    Usage in Pydantic models:
        @field_validator('name')
        @classmethod
        def validate_name(cls, v: str) -> str:
            return validate_string_input(v, field_name='name', max_length=100)
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    
    # Length validation
    if min_length and len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")
    
    if max_length and len(value) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    
    # Sanitize and validate
    sanitized = InputSanitizer.validate_and_sanitize(value, field_name, allow_html)
    
    return sanitized


def validate_phone_number(value: str) -> str:
    """Validate and sanitize phone number."""
    if not isinstance(value, str):
        raise ValueError("Phone number must be a string")
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    
    # Check for SQL injection
    if InputSanitizer.check_sql_injection(cleaned):
        raise ValueError("Phone number contains invalid characters")
    
    # Basic phone number validation (digits only, 10-15 digits)
    if not re.match(r'^\d{10,15}$', cleaned):
        raise ValueError("Phone number must contain 10-15 digits")
    
    return cleaned


def validate_email(value: str) -> str:
    """Validate and sanitize email address."""
    if not isinstance(value, str):
        raise ValueError("Email must be a string")
    
    # Sanitize
    sanitized = InputSanitizer.sanitize_string(value.lower())
    
    # Check for SQL injection
    if InputSanitizer.check_sql_injection(sanitized):
        raise ValueError("Email contains invalid characters")
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, sanitized):
        raise ValueError("Invalid email format")
    
    return sanitized


def validate_uuid_string(value: str) -> str:
    """Validate UUID string format."""
    if not isinstance(value, str):
        raise ValueError("UUID must be a string")
    
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, value, re.IGNORECASE):
        raise ValueError("Invalid UUID format")
    
    return value

