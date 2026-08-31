import logging
import json
from typing import Any, Dict, Optional
from uuid import UUID

from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.value_objects.providers import TelegramProvider
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.providers.telegram.telegram_provider import TelegramProvider as TelegramProviderImpl
from notification_service.domain.entities.tenant.tenant_telegram_configuration import TenantTelegramConfiguration

logger = logging.getLogger(__name__)

class TelegramChannelHandler(IChannelHandler):
    def __init__(
        self,
        unit_of_work: IUnitOfWork,
        telegram_provider: TelegramProviderImpl,
        redis: RedisCache,
    ):
        self.unit_of_work = unit_of_work
        self.redis = redis
        self._handler = {
            TelegramProvider.TELEGRAM: telegram_provider,
        }
        logger.info(f"Initialized TelegramChannelHandler with {len(self._handler)} providers")
    
    async def receiveMessage(
        self,
        tenant_prefix: str,
        message: NotificationRequest,
        isImmediateMode: bool = False,
    ) -> NotificationResponse:
        try:
            logger.info(f"Receiving message for tenant {tenant_prefix} for telegram")
            tenantdb: Tenant = None
            async with self.unit_of_work:
                tenantdb = await self.unit_of_work.tenants.firstOrDefault(lambda t: t.prefix == tenant_prefix)
            
            if not tenantdb:
                logger.error(f"Tenant not found for tenant_prefix: {tenant_prefix}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Tenant with prefix {tenant_prefix} not found"
                )
            
            # Use loadTemplate to get template details
            language = message.lang or "en"
            template_info = await self.loadTemplate(tenantdb.id, message.templateName, language)
            if not template_info:
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Template not found for tenant {tenantdb.id} and language {language}"
                )
            
            templateId = UUID(template_info["templateId"])
            template_body = template_info["templateBody"]
            
            # General Format message
            message_body = template_body.format(**message.payload)
            
            tenantConfigList = await self.loadTenantConfig(tenantdb.id)
            if not tenantConfigList:
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Tenant config not found for tenant {tenantdb.id}"
                )
            
            # Select first active config
            config = next((c for c in tenantConfigList if c.isActive), None)
            if not config:
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Active tenant config not found for tenant {tenantdb.id}"
                )
            
            # Route to provider
            return await self.routeToProvider(
                request=message,
                tenantId=str(tenantdb.id),
                config=config,
                templateId=templateId,
                template=message_body,
                isImmediateMode=isImmediateMode
            )
            
        except Exception as e:
            logger.error(f"Error in receiveMessage for tenant {tenant_prefix}: {str(e)}", exc_info=True)
            return NotificationResponse(
                success=False,
                errorMessage=str(e)
            )

    async def receiveDirectMessage(
        self,
        tenant_prefix: str,
        message: DirectNotificationRequest,
        isImmediateMode: bool = False,
    ) -> NotificationResponse:
        try:
            logger.info(f"Receiving message for tenant {tenant_prefix} for telegram")
            tenantdb: Tenant = None
            async with self.unit_of_work:
                tenantdb = await self.unit_of_work.tenants.firstOrDefault(lambda t: t.prefix == tenant_prefix)
            
            if not tenantdb:
                logger.error(f"Tenant not found for tenant_prefix: {tenant_prefix}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Tenant with prefix {tenant_prefix} not found"
                )
            
            tenantConfig = await self.loadTenantConfig(tenantdb.id)
            if not tenantConfig:
                logger.error(f"Tenant config not found for tenant {tenantdb.id}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Tenant config not found for tenant {tenantdb.id}"
                )
            
            config = next((c for c in tenantConfig if c.isActive), None)
            if not config:
                logger.error(f"Active tenant config not found for tenant {tenantdb.id}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Active tenant config not found for tenant {tenantdb.id}"
                )
            
            provider_name = config.providerName.lower() if hasattr(config, 'providerName') else config.get("providerName", "").lower()
            match provider_name:
                case TelegramProvider.TELEGRAM.value:
                    return await self._handler[TelegramProvider.TELEGRAM].send(
                        requestObject=message,
                        tenantConfig=config,
                        messageToSend=message.body,
                        templateId=None,
                        saveToOutbox=not isImmediateMode,
                    )
                case _:
                    logger.error(f"Provider not found for tenant {tenantdb.id}")
                    return NotificationResponse(
                        success=False,
                        errorMessage=f"Provider not found for tenant {tenantdb.id}"
                    )
        
        except Exception as e:
            logger.error(f"Error in receiveDirectMessage for tenant {tenant_prefix}: {str(e)}")
            return NotificationResponse(
                success=False,
                errorMessage=str(e)
            )

    async def loadTenantConfig(
        self,
        tenantId: UUID,
    ) -> list:
        cache_key = f"tenant_config:{tenantId}:telegram:{TelegramProvider.TELEGRAM.value}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.info(f"Loaded tenant config from cache for tenant {tenantId}")
                return [TenantTelegramConfiguration(**c) for c in cached]
        except Exception as e:
            logger.warning(f"Failed to load tenant config from cache for tenant {tenantId}: {str(e)}")

        async with self.unit_of_work:
            configs = await self.unit_of_work.tenantTelegramConfigurations.find(
                lambda t: t.tenantId == tenantId and t.isActive == True and t.providerName == TelegramProvider.TELEGRAM.value
            )
        
        if configs:
            try:
                config_dicts = [
                    {
                        "id": str(c.id), "tenantId": str(c.tenantId),
                        "providerName": c.providerName, "priority": c.priority,
                        "isActive": c.isActive, "rateLimitPerMinute": c.rateLimitPerMinute,
                        "rateLimitPerHour": c.rateLimitPerHour, "rateLimitPerDay": c.rateLimitPerDay,
                        "config": c.config,
                        "createdAt": c.createdAt.isoformat() if c.createdAt else None,
                        "updatedAt": c.updatedAt.isoformat() if c.updatedAt else None,
                    }
                    for c in configs
                ]
                await self.redis.set(cache_key, json.dumps(config_dicts))
                logger.info(f"Loaded tenant config from DB for tenant {tenantId} and cached it")
                return [TenantTelegramConfiguration(**c) for c in config_dicts]
            except Exception as e:
                logger.error(f"Failed to cache tenant config for tenant {tenantId}: {str(e)}")
                return [TenantTelegramConfiguration(**c) for c in configs]
        else:
            logger.warning(f"No tenant config found for tenant {tenantId}")
            return None

    async def loadTemplate(self, tenantId: str, templateName: str, language: str) -> dict:
        async with self.unit_of_work:
            template = await self.unit_of_work.telegramTemplates.firstOrDefault(
                lambda t: t.tenantId == tenantId and t.templateName == templateName
            )
            if not template:
                logger.error(f"Template not found for tenant {tenantId} and templateName {templateName}")
                return None
            
            template_body = template.content.get(language, None)
            if not template_body:
                # fallback to English
                template_body = template.content.get("en", None)
            if not template_body:
                logger.error(f"Template body not found for tenant {tenantId} and language {language}")
                return None
            
            return {
                "templateId": str(template.id),
                "templateBody": template_body
            }

    async def routeToProvider(
        self,
        request: NotificationRequest,
        tenantId: str,
        config: Dict[str, Any],
        templateId: UUID,
        template: str,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        provider_name = config.providerName.lower() if hasattr(config, 'providerName') else config.get("providerName", "").lower()
        match provider_name:
            case TelegramProvider.TELEGRAM.value:
                return await self._handler[TelegramProvider.TELEGRAM].send(
                    requestObject=request,
                    tenantConfig=config,
                    messageToSend=template,
                    templateId=templateId,
                    saveToOutbox=not isImmediateMode,
                )
            case _:
                logger.error(f"Provider not found for tenant {tenantId}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Provider not found for tenant {tenantId}"
                )