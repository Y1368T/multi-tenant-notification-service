"""
Provider service interface.
Abstraction for third-party notification providers (Twilio, SendGrid, FCM, etc.).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID


class IProviderService(ABC):
    """
    Interface for provider-specific notification delivery.
    Each provider (Twilio, SendGrid, FCM, APNS) implements this interface.
    """
    @abstractmethod
    async def test(self, config: Dict[str, Any],address:str) -> bool:
        pass
    
    @abstractmethod
    async def send(
        self,
        requestObject: Dict[str, Any],
        messageToSend: str,
        templateId:UUID
    ) -> Dict[str, Any]:
        """
        Send notification via provider API.
        
        Args:
            requestObject: Provider-specific request payload
            notificationId: Internal notification ID for tracking
            
        Returns:
            Provider response dict with status, messageId, etc.
            
        Example response:
        {
            "success": true,
            "providerMessageId": "SM1234567890",
            "status": "sent",
            "timestamp": "2024-01-15T10:30:00Z"
        }
        """
        pass
    
    
    
