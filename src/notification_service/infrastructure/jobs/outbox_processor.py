"""
Outbox Background Processor Service.
Polls outbox tables and retries failed notifications with exponential backoff.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional
from uuid import uuid4

from notification_service.config.settings import Settings
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.services.webhook_client import WebhookClient
from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload

logger = logging.getLogger(__name__)


class OutboxProcessor:
    """
    Background service that processes outbox tables for all notification channels.
    
    Polls outbox tables periodically and retries failed messages using exponential backoff.
    """
    
    def __init__(
        self,
        database: Database,
        sms_providers: Dict[str, Any],  # provider_name -> provider instance
        email_provider: Any,  # SMTP provider instance
        inapp_provider: Any,  # FCM provider instance
        settings: Settings,
        webhook_client: Optional[WebhookClient] = None
    ):
        """
        Initialize the OutboxProcessor.
        
        Args:
            database: Database instance for creating UnitOfWork
            sms_providers: Dictionary mapping provider names to provider instances
            email_provider: SMTP email provider instance
            inapp_provider: FCM in-app provider instance
            settings: Application settings
            webhook_client: Optional webhook client for sending callbacks to tenants
        """
        self.database = database
        self.sms_providers = sms_providers
        self.email_provider = email_provider
        self.inapp_provider = inapp_provider
        self.settings = settings
        self.webhook_client = webhook_client or WebhookClient()
        
        # Configuration from settings
        self.poll_interval = settings.outbox_poll_interval_seconds
        self.max_retries = settings.outbox_max_retries
        self.base_retry_delay = settings.outbox_base_retry_delay_minutes
        self.batch_size = settings.outbox_batch_size
        
        # Control flag for graceful shutdown
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def _calculate_next_retry(self, retry_count: int) -> datetime:
        """
        Calculate next retry time using exponential backoff.
        
        Formula: base_delay * 2^retry_count
        
        Example with base_delay=5 minutes:
          retry 1: 5 min
          retry 2: 10 min
          retry 3: 20 min
          retry 4: 40 min
          retry 5: 80 min
        """
        delay_minutes = self.base_retry_delay * (2 ** retry_count)
        return datetime.utcnow() + timedelta(minutes=delay_minutes)
    
    async def _send_tenant_callback(
        self, 
        uow: UnitOfWork,
        tenant_id,
        idempotency_key: str,
        status: str,
        channel: str,
        recipient: str,
        notification_id: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None
    ) -> None:
        """
        Send callback to tenant's configured webhook URL.
        
        Args:
            uow: Unit of work for loading tenant info
            tenant_id: Tenant ID
            idempotency_key: Original idempotency key
            status: Final status (sent, permanently_failed)
            channel: Notification channel (sms, email, inapp)
            recipient: Recipient address
            notification_id: Optional notification ID
            error_message: Optional error message for failures
            retry_count: Optional retry count
        """
        try:
            # Load tenant to get callback URL
            tenant = await uow.tenants.getById(tenant_id)
            if not tenant or not tenant.callbackUrl:
                logger.debug(f"No callback URL configured for tenant {tenant_id}")
                return
            
            # Create callback payload
            payload = NotificationCallbackPayload(
                idempotencyKey=idempotency_key,
                status=status,
                channel=channel,
                recipient=recipient,
                timestamp=datetime.utcnow(),
                notificationId=notification_id,
                errorMessage=error_message,
                retryCount=retry_count
            )
            
            # Send callback
            logger.info(f"Sending callback to tenant {tenant_id} at {tenant.callbackUrl}")
            await self.webhook_client.send_callback(
                callback_url=tenant.callbackUrl,
                payload=payload,
                headers=tenant.callbackHeaders
            )
            
        except Exception as e:
            logger.error(f"Error sending tenant callback for {channel} {idempotency_key}: {e}", exc_info=True)
    
    async def start(self) -> None:
        """Start the background processing loop."""
        self._running = True
        logger.info(
            f"OutboxProcessor started. Poll interval: {self.poll_interval}s, "
            f"Max retries: {self.max_retries}, Base delay: {self.base_retry_delay}min"
        )
        
        while self._running:
            try:
                await self._process_all_outboxes()
            except Exception as e:
                logger.error(f"Error in outbox processing cycle: {e}", exc_info=True)
            
            # Sleep until next poll interval
            await asyncio.sleep(self.poll_interval)
    
    def stop(self) -> None:
        """Signal the processor to stop gracefully."""
        self._running = False
        logger.info("OutboxProcessor stopping...")
    
    async def _process_all_outboxes(self) -> None:
        """Process all outbox tables (SMS, Email, In-App)."""
        logger.debug("Starting outbox processing cycle...")
        
        # Process each channel
        await self._process_sms_outbox()
        await self._process_email_outbox()
        await self._process_inapp_outbox()
        
        logger.debug("Outbox processing cycle completed.")
    
    async def _process_sms_outbox(self) -> None:
        """Process pending SMS outbox messages."""
        try:
            uow = UnitOfWork(self.database)
            async with uow:
                # Query eligible messages
                pending = await uow.smsOutboxes.find(
                    lambda o: (o.status in [NotificationStatus.PENDING, NotificationStatus.FAILED])
                    and o.retryCount < self.max_retries
                    and (o.nextRetryAt is None or o.nextRetryAt <= datetime.utcnow())
                )
                
                if not pending:
                    return
                
                logger.info(f"Found {len(pending)} SMS outbox messages to process")
                
                for outbox in pending[:self.batch_size]:
                    await self._retry_sms_message(uow, outbox)
                    
        except Exception as e:
            logger.error(f"Error processing SMS outbox: {e}", exc_info=True)
    
    async def _retry_sms_message(self, uow: UnitOfWork, outbox) -> None:
        """Retry a single SMS outbox message."""
        tenant_id = None
        try:
            # Load template to get tenant info
            template = await uow.smsTemplates.getById(outbox.templateId)
            if not template:
                logger.error(f"Template not found for SMS outbox {outbox.id}")
                await self._mark_permanently_failed(uow, outbox, "sms", "Template not found")
                return
            
            tenant_id = template.tenantId
            
            # Load tenant config
            configs = await uow.tenantSmsConfigurations.find(
                lambda c: c.tenantId == template.tenantId and c.isActive
            )
            if not configs:
                logger.error(f"No active SMS config found for tenant {template.tenantId}")
                await self._mark_permanently_failed(uow, outbox, "sms", "No active SMS configuration", tenant_id)
                return
            
            # Select provider (priority 1 or lowest priority)
            config = min(configs, key=lambda c: c.priority)
            provider_name = (config.providerName or "").lower()
            
            # Get provider instance
            provider = self.sms_providers.get(provider_name)
            if not provider:
                logger.error(f"SMS provider '{provider_name}' not found")
                await self._mark_permanently_failed(uow, outbox, "sms", f"Provider '{provider_name}' not found", tenant_id)
                return
            
            # Attempt to send
            logger.info(f"Retrying SMS outbox {outbox.id} to {outbox.recipientNumber} via {provider_name}")
            success, error_msg = await provider.send_raw(
                recipient=outbox.recipientNumber,
                message=outbox.messageContent,
                tenantConfig=config
            )
            
            if success:
                # Success - move to notifications table
                await self._move_sms_to_notifications(uow, outbox, template.tenantId)
            else:
                # Failure - update retry info
                await self._update_retry_info(uow, outbox, "sms", error_msg, tenant_id)
                
        except Exception as e:
            logger.error(f"Error retrying SMS outbox {outbox.id}: {e}", exc_info=True)
            await self._update_retry_info(uow, outbox, "sms", str(e), tenant_id)
    
    async def _move_sms_to_notifications(self, uow: UnitOfWork, outbox, tenant_id) -> None:
        """Move successful SMS from outbox to notifications table."""
        try:
            # Create notification record
            notification = SMSNotification(
                id=uuid4(),
                recipientNumber=outbox.recipientNumber,
                messageContent=outbox.messageContent,
                templateId=outbox.templateId,
                status=NotificationStatus.SENT,
                idempotencyKey=outbox.idempotencyKey,
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
            await uow.smsNotifications.add(notification)
            
            # Delete from outbox
            await uow.smsOutboxes.delete(outbox.id)
            await uow.commit()
            
            logger.info(f"SMS outbox {outbox.id} successfully moved to notifications")
            
            # Send callback to tenant if configured
            await self._send_tenant_callback(
                uow=uow,
                tenant_id=tenant_id,
                idempotency_key=outbox.idempotencyKey,
                status="sent",
                channel="sms",
                recipient=outbox.recipientNumber,
                notification_id=str(notification.id),
                retry_count=outbox.retryCount
            )
            
        except Exception as e:
            logger.error(f"Error moving SMS outbox {outbox.id} to notifications: {e}")
            await uow.rollback()
    
    async def _process_email_outbox(self) -> None:
        """Process pending Email outbox messages."""
        try:
            uow = UnitOfWork(self.database)
            async with uow:
                pending = await uow.emailOutbox.find(
                    lambda o: (o.status in [NotificationStatus.PENDING, NotificationStatus.FAILED])
                    and o.retryCount < self.max_retries
                    and (o.nextRetryAt is None or o.nextRetryAt <= datetime.utcnow())
                )
                
                if not pending:
                    return
                
                logger.info(f"Found {len(pending)} Email outbox messages to process")
                
                for outbox in pending[:self.batch_size]:
                    await self._retry_email_message(uow, outbox)
                    
        except Exception as e:
            logger.error(f"Error processing Email outbox: {e}", exc_info=True)
    
    async def _retry_email_message(self, uow: UnitOfWork, outbox) -> None:
        """Retry a single Email outbox message."""
        tenant_id = None
        try:
            # Load template to get tenant info
            template = await uow.emailTemplates.getById(outbox.templateId)
            if not template:
                logger.error(f"Template not found for Email outbox {outbox.id}")
                await self._mark_permanently_failed(uow, outbox, "email", "Template not found")
                return
            
            tenant_id = template.tenantId
            
            # Load tenant config
            configs = await uow.tenantEmailConfigurations.find(
                lambda c: c.tenantId == template.tenantId and c.isActive
            )
            if not configs:
                logger.error(f"No active Email config found for tenant {template.tenantId}")
                await self._mark_permanently_failed(uow, outbox, "email", "No active Email configuration", tenant_id)
                return
            
            config = configs[0]  # Use first active config
            
            # Attempt to send
            logger.info(f"Retrying Email outbox {outbox.id} to {outbox.recipientEmail}")
            success, error_msg = await self.email_provider.send_raw(
                recipient=outbox.recipientEmail,
                messageContent=outbox.messageContent,
                tenantConfig=config
            )
            
            if success:
                await self._move_email_to_notifications(uow, outbox, template.tenantId)
            else:
                await self._update_retry_info(uow, outbox, "email", error_msg, tenant_id)
                
        except Exception as e:
            logger.error(f"Error retrying Email outbox {outbox.id}: {e}", exc_info=True)
            await self._update_retry_info(uow, outbox, "email", str(e), tenant_id)
    
    async def _move_email_to_notifications(self, uow: UnitOfWork, outbox, tenant_id) -> None:
        """Move successful Email from outbox to notifications table."""
        try:
            notification = EmailNotification(
                id=uuid4(),
                recipientEmail=outbox.recipientEmail,
                messageContent=outbox.messageContent,
                templateId=outbox.templateId,
                status=NotificationStatus.SENT,
                idempotencyKey=outbox.idempotencyKey,
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
            await uow.emailNotifications.add(notification)
            await uow.emailOutbox.delete(outbox.id)
            await uow.commit()
            
            logger.info(f"Email outbox {outbox.id} successfully moved to notifications")
            
            # Send callback to tenant if configured
            await self._send_tenant_callback(
                uow=uow,
                tenant_id=tenant_id,
                idempotency_key=outbox.idempotencyKey,
                status="sent",
                channel="email",
                recipient=outbox.recipientEmail,
                notification_id=str(notification.id),
                retry_count=outbox.retryCount
            )
            
        except Exception as e:
            logger.error(f"Error moving Email outbox {outbox.id} to notifications: {e}")
            await uow.rollback()
    
    async def _process_inapp_outbox(self) -> None:
        """Process pending In-App outbox messages."""
        try:
            uow = UnitOfWork(self.database)
            async with uow:
                pending = await uow.inAppOutboxes.find(
                    lambda o: (o.status in [NotificationStatus.PENDING, NotificationStatus.FAILED])
                    and o.retryCount < self.max_retries
                    and (o.nextRetryAt is None or o.nextRetryAt <= datetime.utcnow())
                )
                
                if not pending:
                    return
                
                logger.info(f"Found {len(pending)} In-App outbox messages to process")
                
                for outbox in pending[:self.batch_size]:
                    await self._retry_inapp_message(uow, outbox)
                    
        except Exception as e:
            logger.error(f"Error processing In-App outbox: {e}", exc_info=True)
    
    async def _retry_inapp_message(self, uow: UnitOfWork, outbox) -> None:
        """Retry a single In-App outbox message."""
        tenant_id = None
        try:
            # Load template to get tenant info
            template = await uow.inAppTemplates.getById(outbox.templateId)
            if not template:
                logger.error(f"Template not found for In-App outbox {outbox.id}")
                await self._mark_permanently_failed(uow, outbox, "inapp", "Template not found")
                return
            
            tenant_id = template.tenantId
            
            # Load tenant config
            configs = await uow.tenantInAppConfigurations.find(
                lambda c: c.tenantId == template.tenantId and c.isActive
            )
            if not configs:
                logger.error(f"No active In-App config found for tenant {template.tenantId}")
                await self._mark_permanently_failed(uow, outbox, "inapp", "No active In-App configuration", tenant_id)
                return
            
            config = configs[0]  # Use first active config
            
            # Attempt to send
            logger.info(f"Retrying In-App outbox {outbox.id} to {outbox.recipientUserId}")
            success, error_msg = await self.inapp_provider.send_raw(
                recipient=outbox.recipientUserId,
                messageContent=outbox.messageContent,
                tenantConfig=config
            )
            
            if success:
                await self._move_inapp_to_notifications(uow, outbox, template.tenantId)
            else:
                await self._update_retry_info(uow, outbox, "inapp", error_msg, tenant_id)
                
        except Exception as e:
            logger.error(f"Error retrying In-App outbox {outbox.id}: {e}", exc_info=True)
            await self._update_retry_info(uow, outbox, "inapp", str(e), tenant_id)
    
    async def _move_inapp_to_notifications(self, uow: UnitOfWork, outbox, tenant_id) -> None:
        """Move successful In-App from outbox to notifications table."""
        try:
            notification = InAppNotification(
                id=uuid4(),
                recipientUserId=outbox.recipientUserId,
                messageContent=outbox.messageContent,
                templateId=outbox.templateId,
                status=NotificationStatus.SENT,
                idempotencyKey=outbox.idempotencyKey,
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow()
            )
            await uow.inAppNotifications.add(notification)
            await uow.inAppOutboxes.delete(outbox.id)
            await uow.commit()
            
            logger.info(f"In-App outbox {outbox.id} successfully moved to notifications")
            
            # Send callback to tenant if configured
            await self._send_tenant_callback(
                uow=uow,
                tenant_id=tenant_id,
                idempotency_key=outbox.idempotencyKey,
                status="sent",
                channel="inapp",
                recipient=outbox.recipientUserId,
                notification_id=str(notification.id),
                retry_count=outbox.retryCount
            )
            
        except Exception as e:
            logger.error(f"Error moving In-App outbox {outbox.id} to notifications: {e}")
            await uow.rollback()
    
    async def _update_retry_info(
        self, 
        uow: UnitOfWork, 
        outbox, 
        channel: str, 
        error_msg: str,
        tenant_id = None
    ) -> None:
        """Update outbox retry information after a failed attempt."""
        try:
            outbox.retryCount += 1
            outbox.lastRetryAt = datetime.utcnow()
            outbox.lastErrorMessage = error_msg
            outbox.updatedAt = datetime.utcnow()
            
            if outbox.retryCount >= self.max_retries:
                # Max retries reached - mark as permanently failed
                outbox.status = NotificationStatus.PERMANENTLY_FAILED
                logger.warning(
                    f"{channel.upper()} outbox {outbox.id} marked as permanently failed "
                    f"after {outbox.retryCount} attempts. Last error: {error_msg}"
                )
                
                # Get recipient based on channel for callback
                if channel == "sms":
                    recipient = outbox.recipientNumber
                elif channel == "email":
                    recipient = outbox.recipientEmail
                elif channel == "inapp":
                    recipient = outbox.recipientUserId
                else:
                    recipient = "unknown"
                
                # Send callback to tenant if configured (for permanent failure)
                if tenant_id:
                    await self._send_tenant_callback(
                        uow=uow,
                        tenant_id=tenant_id,
                        idempotency_key=outbox.idempotencyKey,
                        status="permanently_failed",
                        channel=channel,
                        recipient=recipient,
                        error_message=error_msg,
                        retry_count=outbox.retryCount
                    )
            else:
                # Schedule next retry with exponential backoff
                outbox.nextRetryAt = self._calculate_next_retry(outbox.retryCount)
                outbox.status = NotificationStatus.FAILED
                logger.info(
                    f"{channel.upper()} outbox {outbox.id} retry {outbox.retryCount}/{self.max_retries} failed. "
                    f"Next retry at: {outbox.nextRetryAt}"
                )
            
            # Update based on channel
            if channel == "sms":
                await uow.smsOutboxes.update(outbox)
            elif channel == "email":
                await uow.emailOutbox.update(outbox)
            elif channel == "inapp":
                await uow.inAppOutboxes.update(outbox)
            
            await uow.commit()
            
        except Exception as e:
            logger.error(f"Error updating retry info for {channel} outbox {outbox.id}: {e}")
            await uow.rollback()
    
    async def _mark_permanently_failed(
        self, 
        uow: UnitOfWork, 
        outbox, 
        channel: str, 
        reason: str,
        tenant_id = None
    ) -> None:
        """Mark an outbox message as permanently failed and send callback if configured."""
        try:
            outbox.status = NotificationStatus.PERMANENTLY_FAILED
            outbox.lastErrorMessage = reason
            outbox.updatedAt = datetime.utcnow()
            
            if channel == "sms":
                await uow.smsOutboxes.update(outbox)
                recipient = outbox.recipientNumber
            elif channel == "email":
                await uow.emailOutbox.update(outbox)
                recipient = outbox.recipientEmail
            elif channel == "inapp":
                await uow.inAppOutboxes.update(outbox)
                recipient = outbox.recipientUserId
            else:
                recipient = "unknown"
            
            await uow.commit()
            logger.warning(f"{channel.upper()} outbox {outbox.id} marked as permanently failed: {reason}")
            
            # Send callback to tenant if configured
            if tenant_id:
                await self._send_tenant_callback(
                    uow=uow,
                    tenant_id=tenant_id,
                    idempotency_key=outbox.idempotencyKey,
                    status="permanently_failed",
                    channel=channel,
                    recipient=recipient,
                    error_message=reason,
                    retry_count=outbox.retryCount
                )
            
        except Exception as e:
            logger.error(f"Error marking {channel} outbox {outbox.id} as permanently failed: {e}")
            await uow.rollback()

