import logging
from typing import Dict, Any
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import PushProvider
from notification_service.infrastructure.providers.in_app.fcm_provider import FCMProvider
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant.tenant_inapp_configuration import TenantInAppConfiguration
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.entities.in_app.in_app_template import InAppTemplate
from uuid import UUID
import json

logger = logging.getLogger(__name__)

class InAppChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for in-app notification channel"""

    def __init__(self, unitofWork: IUnitOfWork, fcmService: FCMProvider):
        self.unitofWork = unitofWork
        self.__handlers = {
            PushProvider.FIREBASE: fcmService
        }
        logger.info('InAppChannelHandler initialized')
        
    async def receiveMessage(self, tenantPrefix: str, message: NotificationRequest) -> NotificationResponse:
        """Receive a message from the message router."""
        logger.info(f"Receiving in-app message for tenant {tenantPrefix} with template {message.templateName}")
        
        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb = await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(success=False, error_message=f"Tenant with prefix {tenantPrefix} not found")
            
            template = await self.unitofWork.inAppTemplates.firstOrDefault(
                lambda t: t.tenantId == tenantdb.id 
                and t.templateName == message.templateName 
                and t.serviceName == message.serviceName
            )
            if not template:
                logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
                return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
            
            # Check idempotency
            checkIdempotency = await self.unitofWork.inAppNotifications.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey 
                and n.templateId == template.id
            )
            
            if checkIdempotency:
                logger.info(f"Duplicate message detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")
            else:
                logger.info(f"Processing new message for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
        
        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No in-app channel config for tenant {tenantdb.id}")
            return NotificationResponse(success=False, error_message=f"No in-app channel config for tenant {tenantdb.id}")
        
        # Get language preference
        language = message.lang if message.lang else "en"
        template = await self.loadTemplate(tenantdb.id, message.templateName, message.serviceName)
        if not template:
            logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
        
        # Build FCM message from template
        template_body = template.body.get(language, template.body.get("en", {}))
        return await self.routeToProvider(message, tenantdb, tenantConfig, template.id, template_body)

    async def loadTenantConfig(self, tenantId: UUID) -> list[TenantInAppConfiguration]:
        """Load the in-app channel configuration for a given tenant."""
        logger.info(f"Loading in-app channel config for tenant {tenantId}")
        async with self.unitofWork:
            config: list[TenantInAppConfiguration] = await self.unitofWork.tenantInAppConfigurations.find(
                lambda t: t.tenantId == tenantId and t.priority == 1 and t.isActive == True
            )
            if config:
                return config
            return []

    async def loadTemplate(self, tenantId: UUID, templateName: str, serviceName: str) -> InAppTemplate:
        """Load the in-app message template for a given tenant and template name."""
        async with self.unitofWork:
            template = await self.unitofWork.inAppTemplates.firstOrDefault(
                lambda t: t.tenantId == tenantId 
                and t.templateName == templateName 
                and t.serviceName == serviceName
            )
            if not template:
                logger.error(f"Template {templateName} not found for tenant {tenantId}")
                return None
            return template

    async def routeToProvider(
        self,
        request: NotificationRequest,
        tenant: Tenant,
        configs: list[TenantInAppConfiguration],
        templateId: UUID,
        templateBody: Dict[str, Any]
    ) -> NotificationResponse:
        """Route in-app notification to the appropriate provider for delivery."""
        logger.info(f"Routing in-app notification for tenant {tenant.name} to provider")
        
        if not configs:
            logger.error(f"No active in-app configuration found for tenant {tenant.id}")
            return NotificationResponse(success=False, error_message="No active in-app configuration found")
        
        config = configs[0]
        
        # Build FCM message payload from template
        # Template body should contain: title, body, data (optional), android (optional), apns (optional)
        fcm_message = {
            "title": templateBody.get("title", "Notification"),
            "body": templateBody.get("body", ""),
            "data": templateBody.get("data", {}),
            "android": templateBody.get("android", {}),
            "apns": templateBody.get("apns", {})
        }
        
        # Replace placeholders in title and body with actual values from request.payload
        if isinstance(fcm_message["title"], str) and request.payload:
            try:
                fcm_message["title"] = fcm_message["title"].format(**request.payload)
            except KeyError as e:
                logger.warning(f"Missing key in payload for title: {e}")
        
        if isinstance(fcm_message["body"], str) and request.payload:
            try:
                fcm_message["body"] = fcm_message["body"].format(**request.payload)
            except KeyError as e:
                logger.warning(f"Missing key in payload for body: {e}")
        
        # Replace placeholders in data if it's a dict
        if isinstance(fcm_message["data"], dict) and request.payload:
            for key, value in fcm_message["data"].items():
                if isinstance(value, str):
                    try:
                        fcm_message["data"][key] = value.format(**request.payload)
                    except KeyError:
                        pass  # Keep original value if placeholder not found
        
        match config.providerName.lower():
            case PushProvider.FIREBASE.value:
                logger.info(f"Routing to FCM provider for tenant {tenant.name}")
                response = await self.__handlers[PushProvider.FIREBASE].send(
                    request, 
                    config, 
                    fcm_message,
                    templateId
                )
                return response
            case _:
                logger.error(f"Unsupported in-app provider: {config.providerName}")
                return NotificationResponse(
                    success=False, 
                    error_message=f"Unsupported in-app provider: {config.providerName}"
                )

