"""
Application layer exceptions.
Use case and service-level errors.
"""

class ApplicationException(Exception):
    """Base exception for all application-level errors."""
    pass

class MessageRoutingError(ApplicationException):
    """Raised when message routing fails."""
    
    def __init__(self, channel: str, reason: str):
        self.channel = channel
        super().__init__(f"Failed to route message for channel {channel}: {reason}")

class EntityNotFoundError(ApplicationException):
    """Raised when entity is not found (404)."""
    
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id {entity_id} not found")

class ValidationError(ApplicationException):
    """Raised when validation fails (400)."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)

class ConflictError(ApplicationException):
    """Raised when there's a conflict (409)."""
    
    def __init__(self, message: str):
        super().__init__(message)