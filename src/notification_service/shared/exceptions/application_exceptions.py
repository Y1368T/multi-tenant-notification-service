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
