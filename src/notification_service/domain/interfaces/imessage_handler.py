"""
Message handler interface.
Routes messages from queue to appropriate channel handler.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class IMessageHandler(ABC):
    """
    Interface for message routing logic.
    Implements Strategy Pattern for different routing strategies.
    """
    
    @abstractmethod
    async def do_route(self, message: Dict[str, Any], channel: str) -> None:
        """
        Route incoming message to appropriate channel handler.
        
        Args:
            message: Deserialized message from queue
            channel: Notification channel (sms, email, push, whatsapp)
            
        The implementation should:
        1. Validate message structure
        2. Extract tenant information from serviceName
        3. Determine which channel handler to use
        4. Invoke the appropriate channel handler
        """
        pass
