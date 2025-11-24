"""
Example code snippet to add to sms_channel_handler.py
This shows exactly what to change to integrate customer service RPC calls.
"""

# ============================================================================
# STEP 1: Add import at the top of the file (around line 18-19)
# ============================================================================

from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient


# ============================================================================
# STEP 2: Update __init__ method (around line 24-40)
# ============================================================================

class SMSChannelHandler(IChannelHandler):
    """Concrete implementation of IChannelHandler for SMS channel"""

    def __init__(
        self,
        unitofWork: IUnitOfWork,
        afro_service: AfromessageSMSProvider,
        kifiya_service: KifiyaSMSProvider,
        kannel_service: KannelSMSProvider,
        jasmin_service: JasminSMSProvider,
        redis: RedisCache,
        customer_service: Optional[CustomerServiceClient] = None,  # <-- ADD THIS LINE
    ):
        self.unitofWork = unitofWork
        self.redis = redis
        self.customer_service = customer_service  # <-- ADD THIS LINE
        self.__handlers = {
            SMSProvider.AFROMESSAGE: afro_service,
            SMSProvider.KIFIYA: kifiya_service,
            SMSProvider.KANNEL: kannel_service,
            SMSProvider.JASMIN: jasmin_service,
        }


# ============================================================================
# STEP 3: Replace lines 79-80 in receiveMessage method
# ============================================================================

# BEFORE (lines 79-80):
# # send grpc request to customer management service to get customer language preference for Qena system
# language = message.lang if message.lang else "en"

# AFTER:
        # Fetch customer language preference from customer service via RPC
        language = message.lang  # Start with provided language
        
        if not language and self.customer_service:
            # If no language provided, try to fetch from customer service
            # Use first recipient's address as customer identifier
            if message.recipients:
                customer_id = message.recipients[0].address
                try:
                    logger.info(f"Fetching language preference for customer: {customer_id}")
                    language = await self.customer_service.get_customer_language_preference(
                        customer_id=customer_id,
                        tenant_id=str(tenantdb.id),
                        timeout=3.0  # 3 second timeout
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


# ============================================================================
# COMPLETE UPDATED receiveMessage METHOD (for reference)
# ============================================================================

async def receiveMessage(self, tenantPrefix: str, message: NotificationRequest) -> NotificationResponse:
    """Receive a message from the message router."""
    logger.info(f"Receiving SMS message for tenant {tenantPrefix} with template {message.templateName}")
    
    tenantdb: Tenant = None
    async with self.unitofWork:
        tenantdb = await self.unitofWork.tenants.firstOrDefault(lambda t: t.prefix == tenantPrefix)
        if not tenantdb:
            logger.error(f"Tenant with prefix {tenantPrefix} not found")
            return NotificationResponse(success=False, errorMessage=f"Tenant with prefix {tenantPrefix} not found")
            
        template = await self.unitofWork.smsTemplates.firstOrDefault(
            lambda t: t.tenantId == tenantdb.id 
            and t.templateName == message.templateName 
            and t.serviceName == message.serviceName
        )
        if not template:
            logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
            return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
            
        checkIdempotency = await self.unitofWork.smsNotifications.firstOrDefault(
            lambda n: n.idempotencyKey == message.idempotencyKey 
            and n.templateId == template.id
        )
        
        if checkIdempotency:
            logger.error(f"Duplicate message detected for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
            return NotificationResponse(success=True, message="Duplicate message ignored")
        else:
            logger.info(f"Processing new message for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
            checkOutboxIdempotency = await self.unitofWork.smsOutboxes.firstOrDefault(
                lambda n: n.idempotencyKey == message.idempotencyKey 
                and n.templateId == template.id 
                and n.status != "failed"
            )
            if checkOutboxIdempotency:
                logger.info(f"Duplicate message detected in outbox for tenant {tenantPrefix} with idempotency key {message.idempotencyKey}")
                return NotificationResponse(success=True, message="Duplicate message ignored")
                
    tenantConfig = await self.loadTenantConfig(tenantdb.id)
    if not tenantConfig:
        logger.error(f"No SMS channel config for tenant {tenantdb.id}")
        return NotificationResponse(success=False, errorMessage=f"No SMS channel config for tenant {tenantdb.id}")
    
    # ========== UPDATED SECTION: Fetch customer language preference via RPC ==========
    language = message.lang  # Start with provided language
    
    if not language and self.customer_service:
        # If no language provided, try to fetch from customer service
        if message.recipients:
            customer_id = message.recipients[0].address
            try:
                logger.info(f"Fetching language preference for customer: {customer_id}")
                language = await self.customer_service.get_customer_language_preference(
                    customer_id=customer_id,
                    tenant_id=str(tenantdb.id),
                    timeout=3.0
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
    # ========== END UPDATED SECTION ==========
    
    template = await self.loadTemplate(tenantdb.id, message.templateName, message.serviceName)
    if not template:
        logger.error(f"Template {message.templateName} not found for tenant {tenantdb.id}")
        return NotificationResponse(success=False, errorMessage=f"Template {message.templateName} not found for tenant {tenantdb.id}")
    
    templateText = template.content.get(language)
    if templateText is None or templateText.strip() == "":
        logger.error(f"Template text not found for tenant {tenantdb.id} and language {language}")
        return NotificationResponse(success=False, errorMessage=f"Template text not found for tenant {tenantdb.name} and language {language}")
        
    return await self.routeToProvider(message, tenantdb, tenantConfig, template.id, templateText)
