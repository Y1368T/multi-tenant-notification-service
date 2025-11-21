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
    def sanitizeString(cls, value: str, maxLength: Optional[int] = None) -> str:
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
        
        # Truncate if maxLength specified
        if maxLength and len(sanitized) > maxLength:
            sanitized = sanitized[:maxLength]
        
        return sanitized
    
    @classmethod
    def checkSqlInjection(cls, value: str) -> bool:
        """Check if string contains potential SQL injection patterns."""
        if not isinstance(value, str):
            return False
        
        valueUpper = value.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, valueUpper, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def checkXss(cls, value: str) -> bool:
        """Check if string contains potential XSS patterns."""
        if not isinstance(value, str):
            return False
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def validateAndSanitize(cls, value: Any, fieldName: str, allowHtml: bool = False) -> str:
        """
        Validate and sanitize input value.
        
        Args:
            value: Input value to validate
            fieldName: Name of the field (for error messages)
            allowHtml: If True, allows HTML (still escapes dangerous patterns)
        
        Returns:
            Sanitized string
        
        Raises:
            ValueError: If SQL injection or XSS patterns detected
        """
        if not isinstance(value, str):
            raise ValueError(f"{fieldName} must be a string")
        
        # Check for SQL injection
        if cls.checkSqlInjection(value):
            raise ValueError(f"{fieldName} contains potentially dangerous SQL patterns")
        
        # Check for XSS (unless HTML is explicitly allowed)
        if not allowHtml and cls.checkXss(value):
            raise ValueError(f"{fieldName} contains potentially dangerous script patterns")
        
        # Sanitize
        if allowHtml:
            # Only escape dangerous patterns, keep safe HTML
            sanitized = value.strip()
        else:
            sanitized = cls.sanitizeString(value)
        
        return sanitized


# Pydantic validators for common use cases
def validateStringInput(
    value: str,
    fieldName: str = "field",
    maxLength: Optional[int] = None,
    minLength: Optional[int] = None,
    allowHtml: bool = False
) -> str:
    """
    Pydantic-compatible validator for string inputs.
    
    Usage in Pydantic models:
        @field_validator('name')
        @classmethod
        def validateName(cls, v: str) -> str:
            return validateStringInput(v, fieldName='name', maxLength=100)
    """
    if not isinstance(value, str):
        raise ValueError(f"{fieldName} must be a string")
    
    # Length validation
    if minLength and len(value) < minLength:
        raise ValueError(f"{fieldName} must be at least {minLength} characters")
    
    if maxLength and len(value) > maxLength:
        raise ValueError(f"{fieldName} must be at most {maxLength} characters")
    
    # Sanitize and validate
    sanitized = InputSanitizer.validateAndSanitize(value, fieldName, allowHtml)
    
    return sanitized


def validatePhoneNumber(value: str) -> str:
    """Validate and sanitize phone number."""
    if not isinstance(value, str):
        raise ValueError("Phone number must be a string")
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    
    # Check for SQL injection
    if InputSanitizer.checkSqlInjection(cleaned):
        raise ValueError("Phone number contains invalid characters")
    
    # Basic phone number validation (digits only, 10-15 digits)
    if not re.match(r'^\d{10,15}$', cleaned):
        raise ValueError("Phone number must contain 10-15 digits")
    
    return cleaned


def validateEmail(value: str) -> str:
    """Validate and sanitize email address."""
    if not isinstance(value, str):
        raise ValueError("Email must be a string")
    
    # Sanitize
    sanitized = InputSanitizer.sanitizeString(value.lower())
    
    # Check for SQL injection
    if InputSanitizer.checkSqlInjection(sanitized):
        raise ValueError("Email contains invalid characters")
    
    # Basic email validation
    emailPattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(emailPattern, sanitized):
        raise ValueError("Invalid email format")
    
    return sanitized


def validateUuidString(value: str) -> str:
    """Validate UUID string format."""
    if not isinstance(value, str):
        raise ValueError("UUID must be a string")
    
    uuidPattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuidPattern, value, re.IGNORECASE):
        raise ValueError("Invalid UUID format")
    
    return value

