"""Email channel handler for processing email notifications."""
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from notification_service.domain.entities.email.email_template import EmailTemplate
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.direct_notification_request import DirectNotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.value_objects.providers import EmailProvider
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.providers.email.smtp_provider import SMTPProvider
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient

logger = logging.getLogger(__name__)


class EmailChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for Email channel"""

    def __init__(
        self,
        unitofWork: IUnitOfWork,
        smtp_provider: SMTPProvider,
        redis: RedisCache,
        customer_service: CustomerServiceClient,
    ):
        self.unitofWork = unitofWork
        self.customer_service = customer_service
        self.redis = redis
        self.__handlers = {
            EmailProvider.SMTP: smtp_provider,
        }

    async def receiveMessage(
        self, 
        tenantPrefix: str, 
        message: NotificationRequest,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """Receive a message from the message router."""
        logger.info(
            f"Receiving Email message for tenant {tenantPrefix} with template {message.templateName} (immediate={isImmediateMode})"
        )

        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb = await self.unitofWork.tenants.firstOrDefault(
                lambda t: t.prefix == tenantPrefix
            )
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Tenant with prefix {tenantPrefix} not found",
                )

            template = await self.unitofWork.emailTemplates.firstOrDefault(
                lambda t: t.tenantId == tenantdb.id
                and t.templateName == message.templateName
                and t.serviceName == message.serviceName
            )
            if not template:
                logger.error(
                    f"Template {message.templateName} not found for tenant {tenantdb.id}"
                )
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}",
                )

            # Check idempotency in email notifications
            checkIdempotency = await self.unitofWork.emailNotifications.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey
                and n.templateId == template.id
            )

            if checkIdempotency:
                logger.error(
                    f"Duplicate message detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}"
                )
                return NotificationResponse(success=True, message="Duplicate message ignored")
            else:
                logger.info(
                    f"Processing new message for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}"
                )
                # Check outbox for duplicate messages
                checkOutboxIdempotency = await self.unitofWork.emailOutbox.firstOrDefault(
                    lambda n: n.idempotencyKey == message.idempotencyKey
                    and n.templateId == template.id
                    and n.status != "failed"
                )
                if checkOutboxIdempotency:
                    logger.info(
                        f"Duplicate message detected in outbox for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}"
                    )
                    return NotificationResponse(
                        success=True, message="Duplicate message ignored"
                    )

        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No Email channel config for tenant {tenantdb.id}")
            return NotificationResponse(
                success=False,
                errorMessage=f"No Email channel config for tenant {tenantdb.id}",
            )

        # Fetch customer language preference from customer service via RPC
        language = message.lang  # Start with provided language

        if not language:
            customer_id = message.recipient.address
            try:
                logger.info(f"Fetching language preference for customer: {customer_id}")
                phone, language = await self.customer_service.get_customer_language_preference(
                    customer_id=customer_id
                )
                if language:
                    logger.info(
                        f"Fetched language '{language}' for customer {customer_id}"
                    )
                else:
                    logger.info(
                        f"No language preference found for customer {customer_id}, using default"
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch customer language preference: {e}")

        # Fall back to default language if still not set
        if not language:
            language = "en"
            logger.info("Using default language: en")

        template = await self.loadTemplate(
            tenantdb.id, message.templateName, message.serviceName
        )
        if not template:
            logger.error(
                f"Template {message.templateName} not found for tenant {tenantdb.id}"
            )
            return NotificationResponse(
                success=False,
                errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}",
            )

        # Get template body for the language
        templateBody = template.body.get(language)
        if templateBody is None or (isinstance(templateBody, str) and templateBody.strip() == ""):
            logger.error(
                f"Template body not found for tenant {tenantdb.id} and language {language}"
            )
            return NotificationResponse(
                success=False,
                errorMessage=f"Template body not found for tenant {tenantdb.name} and language {language}",
            )

        return await self.routeToProvider(
            message, tenantdb, tenantConfig, template.id, template.subject, templateBody, template.bodyType, isImmediateMode
        )

    async def receiveDirectMessage(
        self,
        tenantPrefix: str,
        message: DirectNotificationRequest,
        isImmediateMode: bool = False,
    ) -> NotificationResponse:
        """Send an email without a pre-defined template."""
        logger.info(f"Receiving direct email for tenant {tenantPrefix} (immediate={isImmediateMode})")

        tenantdb: Tenant = None
        async with self.unitofWork:
            tenantdb = await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
            if not tenantdb:
                logger.error(f"Tenant with prefix {tenantPrefix} not found")
                return NotificationResponse(success=False, errorMessage=f"Tenant with prefix {tenantPrefix} not found")

            checkIdempotency = await self.unitofWork.emailNotifications.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey and n.templateId == None
            )
            if checkIdempotency:
                logger.info(f"Duplicate direct email detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")

            checkOutboxIdempotency = await self.unitofWork.emailOutbox.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey and n.templateId == None and n.status != "failed"
            )
            if checkOutboxIdempotency:
                logger.info(f"Duplicate direct email detected in outbox for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")

        tenantConfig = await self.loadTenantConfig(tenantdb.id)
        if not tenantConfig:
            logger.error(f"No Email channel config for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"No Email channel config for tenant {tenantdb.id}")

        config = min((c for c in tenantConfig if c.isActive), key=lambda c: c.priority, default=None)
        if not config:
            logger.error(f"No active Email configuration found for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage="No active Email configuration found")

        message_to_send = {
            "subject": message.subject,
            "body": message.message,
            "bodyType": "text",
        }

        provider_name = (config.providerName or "").lower()
        match provider_name:
            case EmailProvider.SMTP.value:
                return await self.__handlers[EmailProvider.SMTP].send(
                    message, config, message_to_send, None, saveToOutbox=not isImmediateMode
                )
            case _:
                logger.error(f"Unsupported Email provider: {config.providerName}")
                return NotificationResponse(success=False, errorMessage=f"Unsupported Email provider: {config.providerName}")

    async def loadTenantConfig(self, tenantId: UUID) -> list[TenantEmailConfiguration]:
        """Load the Email channel configuration for a given tenant."""
        logger.info(f"Loading Email channel config for tenant {tenantId}")
        cache_key = f"tenant_config:email:{tenantId}"

        # Try to get from cache first
        try:
            cached_config = await self.redis.get(cache_key)
            if cached_config:
                logger.debug(f"Cache hit for tenant config: {tenantId}")
                # Deserialize from cache
                return [TenantEmailConfiguration(**config) for config in cached_config]
        except Exception as e:
            logger.warning(f"Error reading from cache: {e}, falling back to DB")

        # Load from database
        async with self.unitofWork:
            config: list[TenantEmailConfiguration] = await self.unitofWork.tenantEmailConfigurations.find(
                lambda t: t.tenantId == tenantId and t.priority == 1
            )
            if config:
                # Cache the config (serialize dataclass to dict)
                try:
                    config_dicts = [
                        {
                            "id": str(c.id),
                            "tenantId": str(c.tenantId),
                            "providerName": c.providerName,
                            "priority": c.priority,
                            "isActive": c.isActive,
                            "rateLimitPerMinute": c.rateLimitPerMinute,
                            "rateLimitPerHour": c.rateLimitPerHour,
                            "rateLimitPerDay": c.rateLimitPerDay,
                            "config": c.config,
                            "createdAt": c.createdAt.isoformat() if c.createdAt else None,
                            "updatedAt": c.updatedAt.isoformat() if c.updatedAt else None,
                        }
                        for c in config
                    ]
                    await self.redis.set(
                        cache_key, config_dicts, expire=3600
                    )  # Cache for 1 hour
                    logger.debug(f"Cached tenant config for: {tenantId}")
                except Exception as e:
                    logger.warning(f"Error caching tenant config: {e}")

                return config
            else:
                logger.error(f"No Email channel config found for tenant {tenantId}")
                return []

    async def loadTemplate(
        self, tenantId: UUID, templateName: str, serviceName: str
    ) -> Optional[EmailTemplate]:
        """Load the Email message template for a given tenant and template name."""
        async with self.unitofWork:
            template = await self.unitofWork.emailTemplates.firstOrDefault(
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
        configs: list[TenantEmailConfiguration],
        templateId: UUID,
        subject: str,
        templateBody: str,
        bodyType: str,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """Route Email notification to the appropriate provider for delivery."""
        logger.info(f"Routing Email notification for tenant {tenant.name} to provider (immediate={isImmediateMode})")

        config = configs[0]

        # Select the lowest priority active config
        config = min(
            (c for c in configs if c.isActive),
            key=lambda c: c.priority,
            default=None,
        )

        if not config:
            logger.error(f"No active Email configuration found for tenant {tenant.id}")
            return NotificationResponse(
                success=False, errorMessage="No active Email configuration found"
            )

        provider_name = (config.providerName or "").lower()

        # Format subject with payload
        try:
            formatted_subject = subject.format(**request.payload) if request.payload else subject
        except KeyError as e:
            logger.warning(f"Missing key in payload for subject: {e}")
            formatted_subject = subject

        # Format body with payload
        try:
            formatted_body = templateBody.format(**request.payload) if request.payload else templateBody
        except KeyError as e:
            logger.warning(f"Missing key in payload for body: {e}")
            formatted_body = templateBody

        message_to_send = {
            "subject": formatted_subject,
            "body": formatted_body,
            "bodyType": bodyType,
        }

        match provider_name:
            case EmailProvider.SMTP.value:
                response = await self.__handlers[EmailProvider.SMTP].send(
                    request, config, message_to_send, templateId, saveToOutbox=not isImmediateMode
                )
                return response
            case _:
                logger.error(f"Unsupported Email provider: {config.providerName}")
                return NotificationResponse(
                    success=False,
                    errorMessage=f"Unsupported Email provider: {config.providerName}",
                )
