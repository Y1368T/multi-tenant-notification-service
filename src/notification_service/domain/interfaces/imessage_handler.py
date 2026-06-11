"""
Message handler interface.
Routes messages from queue to appropriate channel handler.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant.tenant import Tenant
class IMessageHandler(ABC):
    """
    Interface for message routing logic.
    Implements Strategy Pattern for different routing strategies.
    """
    
    @abstractmethod
    async def doRoute(self,  channel: NotificationChannel, tenant:str, message: NotificationRequest) -> NotificationResponse:
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

    @abstractmethod
    async def doDirectRoute(
        self,
        channel: NotificationChannel,
        tenant: str,
        message: DirectNotificationRequest,
        isImmediateMode: bool = False,
    ) -> NotificationResponse:
        """
        Route a template-free direct message to the appropriate channel handler.

        Args:
            channel: Notification channel (SMS, EMAIL, INAPP)
            tenant: Tenant prefix
            message: Direct notification request (no template)
            isImmediateMode: If True, caller expects immediate response.
        """
        pass
