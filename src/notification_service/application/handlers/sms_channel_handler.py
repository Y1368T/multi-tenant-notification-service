import logging
from typing import Dict, Any
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.infrastructure.providers.sms.ethiotelecom_shortcode  import EthioTelecomShortcodeSMSProvider
from notification_service.infrastructure.providers.sms.kifiya_sms_gateway  import KifiyaSMSGateway
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.notification_status import NotificationStatus
from uuid import UUID
logger = logging.getLogger(__name__)

class SMSChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for SMS channel"""

    def __init__(self, unitofWork: IUnitOfWork, ethio_service: EthioTelecomShortcodeSMSProvider,kifiya_service:KifiyaSMSGateway):
        self.unitofWork = unitofWork
        self.__handlers = {
            SMSProvider.ETHIOTELECOM: ethio_service,
            SMSProvider.KIFIYA: kifiya_service
        }
        logger.info('SMSChannelHandler initialized')
        
    async def receive_message(self, tenantPrefix: str, message: NotificationRequest) -> NotificationResponse:
        """Receive a message from the message router."""
        logger.info(f"Receiving SMS message for tenant {tenantPrefix} with template {message.template_name}")
        # Implementation for receiving SMS message
        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb= await self.unitofWork.tenants.first_or_default(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(success=False, error_message=f"Tenant with prefix {tenantPrefix} not found")
            if message.idempotency_key is None:
                logger.warning(f"Message for tenant {tenantPrefix} is missing idempotency key. Generating a new one.")
                return NotificationResponse(success=False, error_message="Idempotency key is required")
            check_idempotency=await self.unitofWork.sms_notifications.first_or_default(lambda n: n.idempotency_key == message.idempotency_key and n.tenant_id==tenantdb.id)
            
            if check_idempotency:
                logger.info(f"Duplicate message detected for tenant {tenantPrefix} with idempotency key {message.idempotency_key}")
                return NotificationResponse(success=True, message="Duplicate message ignored")
            elif check_idempotency is None:
                logger.info(f"Processing new message for tenant {tenantPrefix} with idempotency key {message.idempotency_key}")
                check_outbox_idempotency=await self.unitofWork.sms_outbox.first_or_default(lambda n: n.idempotency_key == message.idempotency_key and n.tenant_id==tenantdb.id and n.status!=NotificationStatus.FAILED)
                if check_outbox_idempotency:
                    logger.info(f"Duplicate message detected in outbox for tenant {tenantPrefix} with idempotency key {message.idempotency_key}")
                    return NotificationResponse(success=True, message="Duplicate message ignored")
        tenant_config = await self.load_tenant_config(tenantdb.id)
        if not tenant_config:
            logger.error(f"No SMS channel config for tenant {tenantdb.id}")
            return
        # send grpc request to customer management service to get customer language preference for Qena system
        language = message.lang if message.lang else "en"
        template = await self.load_template(tenantdb.id, message.template_name,message.service_name)
        if not template:
            logger.error(f"Template {message.template_name} not found for tenant {tenantdb.id}")
            return
        
        template_text= template.content.get(language, {})
        return await self.route_to_provider(message, tenantdb, tenant_config, template.id,template_text)

    async def load_tenant_config(self, tenant_id: UUID) -> list[TenantSMSConfiguration]:
        """Load the SMS channel configuration for a given tenant."""
        logger.info(f"Loading SMS channel config for tenant {tenant_id}")
        # Implementation for loading tenant config
        async with self.unitofWork:
            config:list[TenantSMSConfiguration]= await self.unitofWork.tenant_sms_configurations.find(lambda t:t.tenant_id==tenant_id and t.priroty==1)
            if config:
                return config

    

    async def load_template(self, tenant_id: str, template_name: str,service_name:str) -> dict:
        """Load the SMS message template for a given tenant and template name."""
        # Implementation for loading template
        
        async with self.unitofWork:
            template = await self.unitofWork.sms_templates.first_or_default(lambda t: t.tenant_id == tenant_id and t.template_name == template_name  and t.service_name==service_name)
            if not template:
                logger.error(f"Template {template_name} not found for tenant {tenant_id}")
                return {}
            return template

    async def route_to_provider(
        self,
        request: NotificationRequest,
        tenant: Tenant,
        configs: list[TenantSMSConfiguration],
        template_id:UUID,
        template_text: str
    ) -> NotificationResponse:
        """Route SMS notification to the appropriate provider for delivery."""
        # Implementation for routing to SMS provider
        
        logger.info(f"Routing SMS notification for tenant {tenant.name} to provider")
        config=configs[0]
        match config.provider_name.lower():
            case SMSProvider.ETHIOTELECOM.value:
                # Implementation for routing to EThioTelecom
                # replace the message payload in the template with actual values from request. and give me example
                # e.g., Hello {name}, your code is {code} -> Hello John, your code is 1234 and the payload is {'name': 'John', 'code': '1234'}
                
                message_body= template_text.format(**request.payload)
                response= await self.__handlers[SMSProvider.ETHIOTELECOM].send(request, config, message_body,template_id)
                return response
            case SMSProvider.KIFIYA.value:
                # Implementation for routing to EThioTelecom
                # replace the message payload in the template with actual values from request. and give me example
                # e.g., Hello {name}, your code is {code} -> Hello John, your code is 1234 and the payload is {'name': 'John', 'code': '1234'}
                
                message_body= template_text.format(**request.payload)
                response= await self.__handlers[SMSProvider.KIFIYA].send(request, config, message_body,template_id)
                return response
            case _:
                logger.error(f"Unsupported SMS provider: {config.provider_name}")
                
                return NotificationResponse(success=False, error_message=f"Unsupported SMS provider: {config.provider_name}")
        