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
    
    @abstractmethod
    async def callback(
        self,
        providerCallback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process delivery status callback from provider.
        
        Args:
            providerCallback: Webhook payload from provider
            
        Returns:
            Normalized callback data:
            {
                "notificationId": "uuid",
                "status": "delivered",
                "deliveredAt": "2024-01-15T10:30:05Z",
                "errorMessage": null
            }
        """
        pass
    
    @abstractmethod
    async def saveToOutbox(
        self,
        notificationId: str,
        requestObject: Dict[str, Any],
        retryCount: int = 0,
        nextRetryAt: Optional[datetime] = None
    ) -> None:
        """
        Save notification to outbox for guaranteed delivery.
        
        Args:
            notificationId: Internal notification ID
            requestObject: Provider request payload
            retryCount: Current retry attempt number
            nextRetryAt: Scheduled time for next retry
            
        The outbox pattern ensures:
        1. Notifications are persisted before sending
        2. Failed deliveries can be retried
        3. Worker processes can pick up failed messages
        4. Exactly-once delivery semantics
        """
        pass
