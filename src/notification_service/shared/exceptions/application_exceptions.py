"""
Application layer exceptions.
Use case and service-level errors.
"""
from typing import Optional, Dict, Any
from datetime import datetime


class ApplicationException(Exception):
    """Base exception for all application-level errors."""
    
    def __init__(
        self, 
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(message)
    
    def to_error_response(self, status_code: int) -> Dict[str, Any]:
        """Convert exception to standardized error response format."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "type": self.__class__.__name__,
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "details": self.details if self.details else None
            }
        }


class MessageRoutingError(ApplicationException):
    """Raised when message routing fails."""
    
    def __init__(self, channel: str, reason: str):
        self.channel = channel
        code = "MESSAGE_ROUTING_ERROR"
        message = f"Failed to route message for channel {channel}: {reason}"
        details = {"channel": channel, "reason": reason}
        super().__init__(message, code=code, details=details)


class EntityNotFoundError(ApplicationException):
    """Raised when entity is not found (404)."""
    
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        code = "ENTITY_NOT_FOUND"
        message = f"{entity_type} with id {entity_id} not found"
        details = {"entity_type": entity_type, "entity_id": entity_id}
        super().__init__(message, code=code, details=details)


class ValidationError(ApplicationException):
    """Raised when validation fails (400)."""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.field = field
        error_code = code or "VALIDATION_ERROR"
        # Merge field into details if provided, otherwise use provided details
        if details is None:
            details = {"field": field} if field else {}
        elif field and "field" not in details:
            details["field"] = field
        super().__init__(message, code=error_code, details=details)


class ConflictError(ApplicationException):
    """Raised when there's a conflict (409)."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = code or "CONFLICT_ERROR"
        super().__init__(message, code=error_code, details=details or {})


class ValueError(ApplicationException):
    """Raised when a value is invalid (400)."""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.field = field
        error_code = code or "VALUE_ERROR"
        # Merge field into details if provided, otherwise use provided details
        if details is None:
            details = {"field": field} if field else {}
        elif field and "field" not in details:
            details["field"] = field
        super().__init__(message, code=error_code, details=details)