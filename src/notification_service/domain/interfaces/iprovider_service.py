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
        request_object: Dict[str, Any],
        message_to_send: str,
        template_id:UUID
    ) -> Dict[str, Any]:
        """
        Send notification via provider API.
        
        Args:
            request_object: Provider-specific request payload
            notification_id: Internal notification ID for tracking
            
        Returns:
            Provider response dict with status, message_id, etc.
            
        Example response:
        {
            "success": true,
            "provider_message_id": "SM1234567890",
            "status": "sent",
            "timestamp": "2024-01-15T10:30:00Z"
        }
        """
        pass
    
    @abstractmethod
    async def callback(
        self,
        provider_callback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process delivery status callback from provider.
        
        Args:
            provider_callback: Webhook payload from provider
            
        Returns:
            Normalized callback data:
            {
                "notification_id": "uuid",
                "status": "delivered",
                "delivered_at": "2024-01-15T10:30:05Z",
                "error_message": null
            }
        """
        pass
    
    @abstractmethod
    async def save_to_outbox(
        self,
        notification_id: str,
        request_object: Dict[str, Any],
        retry_count: int = 0,
        next_retry_at: Optional[datetime] = None
    ) -> None:
        """
        Save notification to outbox for guaranteed delivery.
        
        Args:
            notification_id: Internal notification ID
            request_object: Provider request payload
            retry_count: Current retry attempt number
            next_retry_at: Scheduled time for next retry
            
        The outbox pattern ensures:
        1. Notifications are persisted before sending
        2. Failed deliveries can be retried
        3. Worker processes can pick up failed messages
        4. Exactly-once delivery semantics
        """
        pass
