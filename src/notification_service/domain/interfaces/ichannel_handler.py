from abc import ABC, abstractmethod
from typing import Any, Dict
from notification_service.domain.value_objects.notification_request import NotificationRequest
class IChannelHandler(ABC):
    """Interface for channel handler operations."""
    
    @abstractmethod
    async def load_tenant_config(self, tenant_id: str) -> dict:
        """Load the channel configuration for a given tenant.
        
        Args:
            tenant_id (str): The tenant identifier.

        Returns:
            dict: The channel configuration for the tenant.
        """
        pass
    @abstractmethod
    async def validate_channel_config(self, config: dict) -> bool:
        """Validate the provided channel configuration.
        
        Args:
            config (dict): The channel configuration to validate.

        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
        pass
    @abstractmethod
    async def load_template(self, tenant_id: str, template_name: str, language: str) -> dict:
        """Load the message template for a given tenant and template name.
        
        Args:
            tenant_id (str): The tenant identifier.
            template_name (str): The name of the template to load.
            language (str): The language code for the template.

        Returns:
            dict: The loaded message template.
        """
        pass

    @abstractmethod
    async def route_to_provider(
        self,
        request: NotificationRequest,
        tenant_id: str,
        config: Dict[str, Any],
       template: str
    ) -> None:
       """
       Route notification to the appropriate provider for delivery.

       Args:
           request: Notification request from external system
           tenant_id: Tenant identifier
           config: Tenant channel configuration
           template: Resolved template string

       The implementation should:
       1. Select provider based on config (primary/fallback)
       2. Construct provider-specific message format
       3. Invoke provider service
       4. Handle provider failures and fallback logic
       5. Save to outbox for guaranteed delivery
       """
       pass
   