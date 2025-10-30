import logging
from typing import Dict, Any
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.Infrastructure.providers.sms  import EthioTelecomShortcodeSMSProvider
logger = logging.getLogger(__name__)

class SMSChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for SMS channel"""

    def __init__(self, unitofWork: IUnitOfWork, ethio_service: EthioTelecomShortcodeSMSProvider):
        self.unitofWork = unitofWork
        self.__handlers = {
            SMSProvider.ETHIOTELECOM: ethio_service
        }
        logger.info('SMSChannelHandler initialized')
        
    async def receive_message(self, tenant: str, message: NotificationRequest) -> NotificationRequest:
        """Receive a message from the message router."""
        logger.info(f"Receiving SMS message for tenant {tenant}")
        # Implementation for receiving SMS message
        tenant = await self.unitofWork.tenants.get_tenant_by_prefix(tenant)
        if not tenant:
            logger.error(f"Tenant with prefix {tenant} not found")
            return
        tenant_config = await self.load_tenant_config(tenant.id)
        if not await self.validate_channel_config(tenant_config):
            logger.error(f"Invalid SMS channel config for tenant {tenant.id}")
            return
        # send grpc request to customer management service to get customer language preference for Qena system
        
        template = await self.load_template(tenant.id, message.template_name, "EN")
        await self.route_to_provider(message, tenant.id, tenant_config, template)

    async def load_tenant_config(self, tenant_id: str) -> dict:
        """Load the SMS channel configuration for a given tenant."""
        logger.info(f"Loading SMS channel config for tenant {tenant_id}")
        # Implementation for loading tenant config
        pass

    async def validate_channel_config(self, config: dict) -> bool:
        """Validate the provided SMS channel configuration."""
        # Implementation for validating config
        pass

    async def load_template(self, tenant_id: str, template_name: str, language: str) -> dict:
        """Load the SMS message template for a given tenant and template name."""
        # Implementation for loading template
        pass

    async def route_to_provider(
        self,
        request: NotificationRequest,
        tenant_id: str,
        config: Dict[str, Any],
        template: str
    ) -> None:
        """Route SMS notification to the appropriate provider for delivery."""
        # Implementation for routing to SMS provider
        
        logger.info(f"Routing SMS notification for tenant {tenant_id} to provider")
        match config.get("provider"):
            case SMSProvider.ETHIOTELECOM.value:
                # Implementation for routing to EThioTelecom
                await self.__handlers[SMSProvider.ETHIOTELECOM].send_sms(request, tenant_id, config, template)
                pass
            case _:
                logger.error(f"Unsupported SMS provider: {config.get('provider')}")
                return 