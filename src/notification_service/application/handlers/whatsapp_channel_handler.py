import logging
from typing import Dict, Any, Optional
from notification_service.domain.entities.whatsapp.whatsapp_template import WhatsAppTemplate
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import WhatsAppProvider
from notification_service.infrastructure.providers.whatsapp.meta_cloud_provider import WhatsAppMetaCloudProvider
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfiguration
from notification_service.domain.value_objects.notification_status import NotificationStatus
from uuid import UUID
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient

logger = logging.getLogger(__name__)

class WhatsAppChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for WhatsApp channel"""

    def __init__(
        self,
        unitofWork: IUnitOfWork,
        meta_cloud_service: WhatsAppMetaCloudProvider,
        redis: RedisCache,
        customer_service: CustomerServiceClient,
    ):
        self.unitofWork = unitofWork
        self.customer_service = customer_service
        self.redis = redis
        self.__handlers = {
            WhatsAppProvider.META_CLOUD: meta_cloud_service,
        }

    async def receiveMessage(
        self,
        tenantPrefix: str,
        message: NotificationRequest,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """Receive a message from the message router."""
        logger.info(f"Receiving WhatsApp message for tenant {tenantPrefix} with template {message.templateName} (immediate={isImmediateMode})")
        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb = await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(success=False, errorMessage=f"Tenant with prefix {tenantPrefix} not found")
            template = await self.unitofWork.whatsAppTemplates.firstOrDefault(
                lambda t: t.tenantId == tenantdb.id
                and t.templateName == message.templateName
                and t.serviceName == message.serviceName
            )
            if not template:
                logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
                return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
            checkIdempotency = await self.unitofWork.whatsAppNotifications.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey
                and n.templateId == template.id
            )

            if checkIdempotency:
                logger.error(f"Duplicate message detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")
            else:
                logger.info(f"Processing new message for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                # Check outbox for duplicate messages using templateId (template already verified to belong to tenant)
                checkOutboxIdempotency = await self.unitofWork.whatsAppOutboxes.firstOrDefault(lambda n: n.idempotencyKey == message.idempotencyKey and n.templateId == template.id and n.status != "failed")
                if checkOutboxIdempotency:
                    logger.info(f"Duplicate message detected in outbox for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                    return NotificationResponse(success=True, message="Duplicate message ignored")
        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No WhatsApp channel config for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"No WhatsApp channel config for tenant {tenantdb.id}")
        # Fetch customer language preference from customer service via RPC
        language = message.lang  # Start with provided language

        if not language:
            # If no language provided, try to fetch from customer service
            customer_id = message.recipient.address
            try:
                logger.info(f"Fetching language preference for customer: {customer_id}")
                phone, language = await self.customer_service.get_customer_language_preference(
                    customer_id=customer_id
                )
                if language:
                    logger.info(f"Fetched language '{language}' for customer {customer_id}")
                else:
                    logger.info(f"No language preference found for customer {customer_id}, using default")
            except Exception as e:
                logger.warning(f"Failed to fetch customer language preference: {e}")

        # Fall back to default language if still not set
        if not language:
            language = "en"
            logger.info("Using default language: en")
        template = await self.loadTemplate(tenantdb.id, message.templateName, message.serviceName)
        if not template:
            logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")

        templateText = template.content.get(language)
        if templateText is None or templateText.strip() == "":
            logger.error(f"Template text not found for tenant {tenantdb.id} and language {language}")
            return NotificationResponse(success=False, errorMessage=f"Template text not found for tenant {tenantdb.name} and language {language}")
        return await self.routeToProvider(message, tenantdb, tenantConfig, template.id, templateText, isImmediateMode)

    async def receiveDirectMessage(
        self,
        tenantPrefix: str,
        message: DirectNotificationRequest,
        isImmediateMode: bool = False,
    ) -> NotificationResponse:
        """Send a WhatsApp message without a pre-defined template."""
        logger.info(f"Receiving direct WhatsApp message for tenant {tenantPrefix} (immediate={isImmediateMode})")

        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb = await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(success=False, errorMessage=f"Tenant with prefix {tenantPrefix} not found")

            checkIdempotency = await self.unitofWork.whatsAppNotifications.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey and n.templateId == None
            )
            if checkIdempotency:
                logger.info(f"Duplicate direct WhatsApp message detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")

            checkOutboxIdempotency = await self.unitofWork.whatsAppOutboxes.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey and n.templateId == None and n.status != "failed"
            )
            if checkOutboxIdempotency:
                logger.info(f"Duplicate direct WhatsApp message detected in outbox for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")

        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No WhatsApp channel config for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"No WhatsApp channel config for tenant {tenantdb.id}")

        config = None
        if message.metadata and message.metadata.get("shortcode"):
            config = next(
                (c for c in tenantConfig if (c.config.get("shortcode") or "").lower() == (message.metadata.get("shortcode") or "").lower()),
                None,
            )
            if not config:
                logger.error(f"No config found for shortcode '{message.metadata.get('shortcode')}' in tenant {tenantdb.name}")
                return NotificationResponse(success=False, errorMessage=f"No config found for shortcode '{message.metadata.get('shortcode')}'")
        else:
            config = min((c for c in tenantConfig if c.isActive), key=lambda c: c.priority, default=None)

        if not config:
            logger.error(f"No active WhatsApp configuration found for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage="No active WhatsApp configuration found")

        provider_name = (config.providerName or "").lower()
        match provider_name:
            case WhatsAppProvider.META_CLOUD.value:
                return await self.__handlers[WhatsAppProvider.META_CLOUD].send(
                    message, config, message.message, None, saveToOutbox=not isImmediateMode
                )
            case _:
                logger.error(f"Unsupported WhatsApp provider: {config.providerName}")
                return NotificationResponse(success=False, errorMessage=f"Unsupported WhatsApp provider: {config.providerName}")

    async def loadTenantConfig(self, tenantId: UUID) -> list[TenantWhatsAppConfiguration]:
        """Load the WhatsApp channel configuration for a given tenant."""
        logger.info(f"Loading WhatsApp channel config for tenant {tenantId}")
        cache_key = f"tenant_config:whatsapp:{tenantId}"

        # Try to get from cache first
        try:
            cached_config = await self.redis.get(cache_key)
            if cached_config:
                logger.debug(f"Cache hit for tenant config: {tenantId}")
                # Deserialize from cache
                return [TenantWhatsAppConfiguration(**config) for config in cached_config]
        except Exception as e:
            logger.warning(f"Error reading from cache: {e}, falling back to DB")

        # Load from database
        async with self.unitofWork:
            config: list[TenantWhatsAppConfiguration] = await self.unitofWork.tenantWhatsAppConfigurations.find(
                lambda t: t.tenantId == tenantId and t.priority == 1
            )
            if config:
                # Cache the config (serialize dataclass to dict)
                try:
                    config_dicts = [
                        {
                            'id': str(c.id),
                            'tenantId': str(c.tenantId),
                            'providerName': c.providerName,
                            'priority': c.priority,
                            'isActive': c.isActive,
                            'rateLimitPerMinute': c.rateLimitPerMinute,
                            'rateLimitPerHour': c.rateLimitPerHour,
                            'rateLimitPerDay': c.rateLimitPerDay,
                            'config': c.config,
                            'createdAt': c.createdAt.isoformat() if c.createdAt else None,
                            'updatedAt': c.updatedAt.isoformat() if c.updatedAt else None,
                        }
                        for c in config
                    ]
                    await self.redis.set(cache_key, config_dicts, expire=3600)  # Cache for 1 hour
                    logger.debug(f"Cached tenant config for: {tenantId}")
                except Exception as e:
                    logger.warning(f"Error caching tenant config: {e}")

                return config
            else:
                logger.error(f"No WhatsApp channel config found for tenant {tenantId}")
                return []

    async def loadTemplate(self, tenantId: UUID, templateName: str, serviceName: str) -> Optional[WhatsAppTemplate]:
        """Load the WhatsApp message template for a given tenant and template name."""
        async with self.unitofWork:
            template = await self.unitofWork.whatsAppTemplates.firstOrDefault(lambda t: t.tenantId == tenantId and t.templateName == templateName and t.serviceName == serviceName)
            if not template:
                logger.error(f"Template {templateName} not found for tenant {tenantId}")
                return None
            return template

    async def routeToProvider(
        self,
        request: NotificationRequest,
        tenant: Tenant,
        configs: list[TenantWhatsAppConfiguration],
        templateId: UUID,
        templateText: str,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """Route WhatsApp notification to the appropriate provider for delivery."""
        logger.info(f"Routing WhatsApp notification for tenant {tenant.name} to provider (immediate={isImmediateMode})")
        config = configs[0]
        if request.metadata and request.metadata.get("shortcode"):
            config = next((c for c in configs if (c.config.get("shortcode") or "").lower() == (request.metadata.get("shortcode") or "").lower()), None)
            if not config:
                logger.error(f"No config found for shortcode '{request.metadata.get('shortcode')}' in tenant {tenant.name}")
                return NotificationResponse(success=False, errorMessage=f"No config found for shortcode '{request.metadata.get('shortcode')}'")
        else:
            # select the lowest priority active config
            config = min(
                (c for c in configs if c.isActive),
                key=lambda c: c.priority,
                default=None
            )

        provider_name = (config.providerName or "").lower()

        match provider_name:
            case WhatsAppProvider.META_CLOUD.value:
                # replace the message payload in the template with actual values from request
                # e.g., Hello {name}, your code is {code} -> Hello John, your code is 1234 and the payload is {'name': 'John', 'code': '1234'}
                message_body = templateText.format(**request.payload)
                response = await self.__handlers[WhatsAppProvider.META_CLOUD].send(
                    request, config, message_body, templateId, saveToOutbox=not isImmediateMode
                )
                return response
            case _:
                logger.error(f"Unsupported WhatsApp provider: {config.providerName}")
                return NotificationResponse(success=False, errorMessage=f"Unsupported WhatsApp provider: {config.providerName}")
