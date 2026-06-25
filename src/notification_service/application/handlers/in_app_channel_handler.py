import logging
from typing import Dict, Any
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
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
from notification_service.infrastructure.cache.redis_cache import RedisCache
logger = logging.getLogger(__name__)

class InAppChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for in-app notification channel"""

    def __init__(self, unitofWork: IUnitOfWork, fcmService: FCMProvider, redis: RedisCache):
        self.unitofWork = unitofWork
        self.redis = redis
        self.__handlers = {
            PushProvider.FIREBASE: fcmService
        }
        logger.info('InAppChannelHandler initialized')
        
    async def receiveMessage(
        self, 
        tenantPrefix: str, 
        message: NotificationRequest,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """Receive a message from the message router."""
        logger.info(f"Receiving in-app message for tenant {tenantPrefix} with template {message.templateName} (immediate={isImmediateMode})")
        
        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb = await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(success=False, errorMessage=f"Tenant with prefix {tenantPrefix} not found")
            
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
                return NotificationResponse(success=False, errorMessage="Duplicate message ignored")
            else:
                logger.info(f"Processing new message for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
        
        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No in-app channel config for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"No in-app channel config for tenant {tenantdb.id}")
        
        # Get language preference
        language = message.lang if message.lang else "en"
        template = await self.loadTemplate(tenantdb.id, message.templateName, message.serviceName)
        if not template:
            logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
        
        # Build FCM message from template
        template_body = template.body.get(language, template.body.get("en", {}))
        return await self.routeToProvider(message, tenantdb, tenantConfig, template.id, template_body, isImmediateMode)

    async def receiveDirectMessage(
        self,
        tenantPrefix: str,
        message: DirectNotificationRequest,
        isImmediateMode: bool = False,
    ) -> NotificationResponse:
        """Send an in-app notification without a pre-defined template."""
        logger.info(f"Receiving direct in-app notification for tenant {tenantPrefix} (immediate={isImmediateMode})")

        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb = await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(success=False, errorMessage=f"Tenant with prefix {tenantPrefix} not found")

            checkIdempotency = await self.unitofWork.inAppNotifications.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey and n.templateId == None
            )
            if checkIdempotency:
                logger.info(f"Duplicate direct in-app notification detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")

        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No in-app channel config for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"No in-app channel config for tenant {tenantdb.id}")

        fcm_message = {
            "title": message.title or "",
            "body": message.message,
            "data": {},
            "android": {},
            "apns": {},
        }

        config = tenantConfig[0]
        match config.providerName.lower():
            case PushProvider.FIREBASE.value:
                return await self.__handlers[PushProvider.FIREBASE].send(
                    message, config, fcm_message, None, saveToOutbox=not isImmediateMode
                )
            case _:
                logger.error(f"Unsupported in-app provider: {config.providerName}")
                return NotificationResponse(success=False, errorMessage=f"Unsupported in-app provider: {config.providerName}")

    async def loadTenantConfig(self, tenantId: UUID) -> list[TenantInAppConfiguration]:
        """Load the in-app channel configuration for a given tenant."""
        logger.info(f"Loading in-app channel config for tenant {tenantId}")
        cache_key = f"tenant_config:in_app:{tenantId}"
        cached_config = await self.redis.get(cache_key)
        if cached_config:
            logger.info(f"Cache hit for in-app channel config: {tenantId}")
            return [TenantInAppConfiguration(**config) for config in cached_config]
        else:
            logger.info(f"Cache miss for in-app channel config: {tenantId}")
        async with self.unitofWork:
            config: list[TenantInAppConfiguration] = await self.unitofWork.tenantInAppConfigurations.find(
                lambda t: t.tenantId == tenantId and t.priority == 1 and t.isActive == True
            )
        if config:
            await self.redis.set(cache_key, [config.__dict__ for config in config], expire=60*60*24)
        return config
            

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
        templateBody: Dict[str, Any],
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """Route in-app notification to the appropriate provider for delivery."""
        logger.info(f"Routing in-app notification for tenant {tenant.name} to provider (immediate={isImmediateMode})")
        
        if not configs:
            logger.error(f"No active in-app configuration found for tenant {tenant.id}")
            return NotificationResponse(success=False, errorMessage="No active in-app configuration found")
        
        config = configs[0]
        
        # Extract platform configs from template (stored with _ prefix in body)
        # These are top-level fields that apply to all languages
        platform_data = templateBody.get('data')
        platform_android = templateBody.get('android')
        platform_apns = templateBody.get('apns')
        
        # Build FCM message payload from template
        # templateBody contains language-specific title and body/message
        fcm_message = {
            "title": templateBody.get("title", "Notification"),
            "body": templateBody.get("body", templateBody.get("message", "")),
            "data": platform_data if platform_data is not None else {},
            "android": platform_android if platform_android is not None else {},
            "apns": platform_apns if platform_apns is not None else {}
        }
        
        # Helper function to recursively format placeholders in nested dictionaries
        def formatPlaceholders(obj, payload: Dict[str, Any]):
            """Recursively format placeholders in nested dict/list structures."""
            if isinstance(obj, dict):
                return {k: formatPlaceholders(v, payload) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [formatPlaceholders(item, payload) for item in obj]
            elif isinstance(obj, str) and payload:
                try:
                    return obj.format(**payload)
                except (KeyError, ValueError):
                    # If formatting fails, return original string
                    return obj
            else:
                return obj
        
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
        
        # Format placeholders in data (recursively handles nested structures)
        if fcm_message["data"] and request.payload:
            fcm_message["data"] = formatPlaceholders(fcm_message["data"], request.payload)
        
        # Format placeholders in android config (recursively handles nested structures)
        if fcm_message["android"] and request.payload:
            fcm_message["android"] = formatPlaceholders(fcm_message["android"], request.payload)
        
        # Format placeholders in apns config (recursively handles nested structures)
        if fcm_message["apns"] and request.payload:
            fcm_message["apns"] = formatPlaceholders(fcm_message["apns"], request.payload)
        
        match config.providerName.lower():
            case PushProvider.FIREBASE.value:
                logger.info(f"Routing to FCM provider for tenant {tenant.name}")
                response = await self.__handlers[PushProvider.FIREBASE].send(
                    request, 
                    config, 
                    fcm_message,
                    templateId,
                    saveToOutbox=not isImmediateMode
                )
                return response
            case _:
                logger.error(f"Unsupported in-app provider: {config.providerName}")
                return NotificationResponse(
                    success=False, 
                    errorMessage=f"Unsupported in-app provider: {config.providerName}"
                )

