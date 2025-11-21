"""
Standardized error response format for all exceptions.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ErrorResponse:
    """
    Standardized error response format.
    
    Example:
    {
        "error": {
            "code": "ENTITY_NOT_FOUND",
            "message": "Tenant with id 123 not found",
            "type": "EntityNotFoundError",
            "status_code": 404,
            "timestamp": "2024-01-15T10:30:00Z",
            "details": {
                "entity_type": "Tenant",
                "entity_id": "123"
            }
        }
    }
    """
    code: str
    message: str
    type: str
    status_code: int
    timestamp: str
    details: Optional[Dict[str, Any]] = None
    
    def toDict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON response."""
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
                "type": self.type,
                "status_code": self.status_code,
                "timestamp": self.timestamp
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result

from .application_exceptions import (
    ApplicationException,
    MessageRoutingError,
    EntityNotFoundError,
    ValidationError,
    ConflictError,
    ValueError
)

__all__ = [
    "ApplicationException",
    "MessageRoutingError",
    "EntityNotFoundError",
    "ValidationError",
    "ConflictError",
    "ValueError"
]