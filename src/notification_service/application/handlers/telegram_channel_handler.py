import logging
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
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration

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
                tenantdb = await self.unit_of_work.tenants.firstOrDefault(lambda t: t.tenant_prefix == tenant_prefix)
            
                if not tenantdb:
                    logger.error(f"Tenant not found for tenant_prefix: {tenant_prefix}")
                    return NotificationResponse(
                        success=False,
                        errorMessage=f"Tenant with prefix {tenant_prefix} not found"
                    )
                template = await self.unit_of_work.smsTemplates.firstOrDefault(
                    lambda t: t.tenantId == tenantdb.id
                    and t.templateName == message.templateName
                    and t.serviceName == message.serviceName
                )
                if not template:
                    logger.error(f"Template not found for tenant {tenantdb.id} and templateName {message.templateName} and serviceName {message.serviceName}")
                    return NotificationResponse(
                        success=False,
                        errorMessage=f"Template not found for tenant {tenantdb.id} and templateName {message.templateName} and serviceName {message.serviceName}"
                    )
                
                checkIdempotency = await self.unit_of_work.smsNotifications.firstOrDefault(
                    lambda n: n.idempotencyKey == message.idempotencyKey
                    and n.templateId == template.id
                )
                if checkIdempotency:
                    return NotificationResponse(
                        success=True,
                        message="Notification already sent."
                    )
            
            tenantConfig = await self.loadTenantConfig(tenantdb.id)
            if not tenantConfig:
                logger.error(f"Tenant config not found for tenant {tenantdb.id}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Tenant config not found for tenant {tenantdb.id}"
                )

            language = message.lang or "en"
            template_body = template.contents.get(language, None)
            if not template_body:
                logger.error(f"Template body not found for tenant {tenantdb.id} and language {language}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Template body not found for tenant {tenantdb.id} and language {language}"
                )
            
            message_body = template_body.format(**message.payload)
            config = tenantConfig.get(TelegramProvider.TELEGRAM.value)
            if not config:
                logger.error(f"Tenant config not found for tenant {tenantdb.id}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Tenant config not found for tenant {tenantdb.id}"
                )
            
            match config.providerName.lower():
                case TelegramProvider.TELEGRAM.value:
                    return await self._handler[TelegramProvider.TELEGRAM].sendMessage(
                        tenantConfig=tenantConfig,
                        message=message,
                        template=template,
                        messageBody=message_body,
                        isImmediateMode=isImmediateMode,
                        tenantId=tenantdb.id,
                    )
                case _:
                    logger.error(f"Provider not found for tenant {tenantdb.id}")
                    return NotificationResponse(
                        success=False,
                        errorMessage=f"Provider not found for tenant {tenantdb.id}"
                    )
            
        except Exception as e:
            logger.error(f"Error in receiveMessage for tenant {tenant_prefix}: {str(e)}")
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
                    tenantdb = await self.unit_of_work.tenants.firstOrDefault(lambda t: t.tenant_prefix == tenant_prefix)
                
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
                
                config = tenantConfig.get(TelegramProvider.TELEGRAM.value)
                if not config:
                    logger.error(f"Tenant config not found for tenant {tenantdb.id}")
                    return NotificationResponse(
                        success=False,
                        errorMessage=f"Tenant config not found for tenant {tenantdb.id}"
                    )
                
                match config.providerName.lower():
                    case TelegramProvider.TELEGRAM.value:
                        return await self._handler[TelegramProvider.TELEGRAM].sendMessage(
                            tenantConfig=tenantConfig,
                            message=message,
                            template=None,
                            messageBody=message.body,
                            isImmediateMode=isImmediateMode,
                            tenantId=tenantdb.id,
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
                    return [TenantSMSConfiguration(**c) for c in cached]
            except Exception as e:
                logger.warning(f"Failed to load tenant config from cache for tenant {tenantId}: {str(e)}")

            async with self.unit_of_work:
                configs = await self.unit_of_work.tenantSMSConfigurations.find(
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
                    return [TenantSMSConfiguration(**c) for c in config_dicts]
                except Exception as e:
                    logger.error(f"Failed to cache tenant config for tenant {tenantId}: {str(e)}")
                    return [c for c in configs]
            else:
                logger.warning(f"No tenant config found for tenant {tenantId}")
                return None
            
            