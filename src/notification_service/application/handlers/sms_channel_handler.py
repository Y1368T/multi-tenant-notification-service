import logging
from typing import Dict, Any, Optional
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.infrastructure.providers.sms.afromessage_provider import AfromessageSMSProvider
from notification_service.infrastructure.providers.sms.kifiyaSmsProvider  import KifiyaSMSProvider
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.notification_status import NotificationStatus
from uuid import UUID
logger = logging.getLogger(__name__)

class SMSChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for SMS channel"""

    def __init__(self, unitofWork: IUnitOfWork, afro_service: AfromessageSMSProvider, kifiya_service: KifiyaSMSProvider):
        self.unitofWork = unitofWork
        self.__handlers = {
            SMSProvider.AFROMESSAGE: afro_service,
            SMSProvider.KIFIYA: kifiya_service
        }
        
    async def receiveMessage(self, tenantPrefix: str, message: NotificationRequest) -> NotificationResponse:
        """Receive a message from the message router."""
        logger.info(f"Receiving SMS message for tenant {tenantPrefix} with template {message.templateName}")
        # Implementation for receiving SMS message
        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb= await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")  # pyright: ignore[reportUnreachable]
                return NotificationResponse(success=False, error_message=f"Tenant with prefix {tenantPrefix} not found")
            template = await self.unitofWork.smsTemplates.firstOrDefault(
                lambda t: t.tenantId == tenantdb.id 
                and t.templateName == message.templateName 
                and t.serviceName == message.serviceName
            )
            if not template:
                logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
                return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
            checkIdempotency=await self.unitofWork.smsNotifications.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey 
                and n.templateId==template.id
            )
            
            if checkIdempotency:
                logger.error(f"Duplicate message detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")
            else:
                logger.info(f"Processing new message for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                # Check outbox for duplicate messages using templateId (template already verified to belong to tenant)
                checkOutboxIdempotency=await self.unitofWork.smsOutboxes.firstOrDefault(lambda n: n.idempotencyKey == message.idempotencyKey and n.templateId==template.id and n.status!="failed")
                if checkOutboxIdempotency:
                    logger.info(f"Duplicate message detected in outbox for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                    return NotificationResponse(success=True, message="Duplicate message ignored")
        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No SMS channel config for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"No SMS channel config for tenant {tenantdb.id}")
        # send grpc request to customer management service to get customer language preference for Qena system
        language = message.lang if message.lang else "en"
        template = await self.loadTemplate(tenantdb.id, message.templateName,message.serviceName)
        if not template:
            logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
        
        templateText= template.content.get(language)
        if templateText is None or templateText.strip() == "":
            logger.error(f"Template text not found for tenant {tenantdb.id} and language {language}")
            return NotificationResponse(success=False, errorMessage=f"Template text not found for tenant {tenantdb.name} and language {language}")
        return await self.routeToProvider(message, tenantdb, tenantConfig, template.id, templateText)

    async def loadTenantConfig(self, tenantId: UUID) -> list[TenantSMSConfiguration]:
        """Load the SMS channel configuration for a given tenant."""
        logger.info(f"Loading SMS channel config for tenant {tenantId}")
        # Implementation for loading tenant config
        async with self.unitofWork:
            config:list[TenantSMSConfiguration]= await self.unitofWork.tenantSmsConfigurations.find(lambda t:t.tenantId==tenantId and t.priority==1)
            if config:
                return config
            else:
                logger.error(f"No SMS channel config found for tenant {tenantId}")
                return None
    

    async def loadTemplate(self, tenantId: UUID, templateName: str,serviceName:str) -> Optional[SmsTemplate]:
        """Load the SMS message template for a given tenant and template name."""
        # Implementation for loading template
        
        async with self.unitofWork:
            template = await self.unitofWork.smsTemplates.firstOrDefault(lambda t: t.tenantId == tenantId and t.templateName == templateName  and t.serviceName==serviceName)
            if not template:
                logger.error(f"Template {templateName} not found for tenant {tenantId}")
                return None
            return template

    async def routeToProvider(
        self,
        request: NotificationRequest,
        tenant: Tenant,
        configs: list[TenantSMSConfiguration],
        templateId:UUID,
        templateText: str
    ) -> NotificationResponse:
        """Route SMS notification to the appropriate provider for delivery."""
        # Implementation for routing to SMS provider
        
        logger.info(f"Routing SMS notification for tenant {tenant.name} to provider")
        config=configs[0]
        match config.providerName.lower():
            case SMSProvider.AFROMESSAGE.value:
                # Implementation for routing to Afromessage
                # replace the message payload in the template with actual values from request. and give me example
                # e.g., Hello {name}, your code is {code} -> Hello John, your code is 1234 and the payload is {'name': 'John', 'code': '1234'}
                
                message_body= templateText.format(**request.payload)
                response= await self.__handlers[SMSProvider.AFROMESSAGE].send(request, config, message_body,templateId)
                return response
            case SMSProvider.KIFIYA.value:
                # Implementation for routing to Kifiya
                # replace the message payload in the template with actual values from request. and give me example
                # e.g., Hello {name}, your code is {code} -> Hello John, your code is 1234 and the payload is {'name': 'John', 'code': '1234'}
                
                message_body= templateText.format(**request.payload)
                response= await self.__handlers[SMSProvider.KIFIYA].send(request, config, message_body,templateId)
                return response
            case _:
                logger.error(f"Unsupported SMS provider: {config.providerName}")
                
                return NotificationResponse(success=False, error_message=f"Unsupported SMS provider: {config.providerName}")
        