from abc import ABC, abstractmethod
from typing import Any, Dict
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from uuid import UUID

class IChannelHandler(ABC):
    """Interface for channel handler operations."""
    
    @abstractmethod
    async def receiveMessage(
        self, 
        tenantPrefix: str, 
        message: NotificationRequest,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """Receive a message from the message router.
        
        Args:
            tenantPrefix: Tenant prefix identifier
            message: Notification request
            isImmediateMode: If True, caller expects immediate response and handles retry.
                           If False, failed messages go to outbox for automatic retry.

        Returns:
            NotificationResponse: The notification processing result.
        """
        pass

    @abstractmethod
    async def loadTenantConfig(self, tenantId: str) -> dict:
        """Load the channel configuration for a given tenant.
        
        Args:
            tenantId (str): The tenant identifier.

        Returns:
            dict: The channel configuration for the tenant.
        """
        pass
    
    @abstractmethod
    async def loadTemplate(self, tenantId: str, templateName: str, language: str) -> dict:
        """Load the message template for a given tenant and template name.
        
        Args:
            tenantId (str): The tenant identifier.
            templateName (str): The name of the template to load.
            language (str): The language code for the template.

        Returns:
            dict: The loaded message template.
        """
        pass

    @abstractmethod
    async def routeToProvider(
        self,
        request: NotificationRequest,
        tenantId: str,
        config: Dict[str, Any],
        templateId: UUID,
        template: str,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
       """
       Route notification to the appropriate provider for delivery.

       Args:
           request: Notification request from external system
           tenant_id: Tenant identifier
           config: Tenant channel configuration
           templateId: Template ID
           template: Resolved template string
           isImmediateMode: If True, don't save to outbox on failure.
                          If False, save to outbox for automatic retry.

       The implementation should:
       1. Select provider based on config (primary/fallback)
       2. Construct provider-specific message format
       3. Invoke provider service
       4. Handle provider failures and fallback logic
       5. Save to outbox for guaranteed delivery (only if isImmediateMode=False)
       """
       pass
   