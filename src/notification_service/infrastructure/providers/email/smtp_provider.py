"""SMTP Email Provider implementation following the same pattern as SMS providers."""
import asyncio
import logging
import smtplib
import ssl
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from notification_service.domain.entities.email.email_notification import EmailNotification
from notification_service.domain.entities.email.email_outbox import EmailOutbox
from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import (
    NotifiationResponsePerRecipient,
    NotificationResponse,
    ProviderTestResponse,
)
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload
from uuid import UUID

from notification_service.infrastructure.services.webhook_client import WebhookClient

logger = logging.getLogger(__name__)


class SMTPConfiguration(BaseModel):
    """Configuration settings for SMTP Email provider."""
    host: str
    port: int = 587
    username: str
    password: str
    fromEmail: str
    fromName: str = ""
    useTls: bool = True
    useSsl: bool = False
    timeout: int = 30

    class Config:
        from_attributes = True

    def toDict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "fromEmail": self.fromEmail,
            "fromName": self.fromName,
            "useTls": self.useTls,
            "useSsl": self.useSsl,
            "timeout": self.timeout,
        }

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "SMTPConfiguration":
        return cls(
            host=data.get("host", ""),
            port=data.get("port", 587),
            username=data.get("username", ""),
            password=data.get("password", ""),
            fromEmail=data.get("fromEmail", ""),
            fromName=data.get("fromName", ""),
            useTls=data.get("useTls", True),
            useSsl=data.get("useSsl", False),
            timeout=data.get("timeout", 30),
        )


class SMTPProvider(IProviderService):
    """SMTP Email provider implementation."""

    def __init__(self, uow: IUnitOfWork, webhook_client: WebhookClient):
        self.uow = uow
        self.webhook_client = webhook_client

    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        """Test SMTP configuration by sending a test email."""
        try:
            smtp_config = SMTPConfiguration.fromDict(config)

            # Create a test message
            message = MIMEMultipart("alternative")
            message["Subject"] = "Test Email from Notification Service"
            message["From"] = (
                f"{smtp_config.fromName} <{smtp_config.fromEmail}>"
                if smtp_config.fromName
                else smtp_config.fromEmail
            )
            message["To"] = address

            # Create plain text and HTML versions
            text_content = "This is a test email from the Notification Service."
            html_content = """
            <html>
                <body>
                    <h1>Test Email</h1>
                    <p>This is a test email from the Notification Service.</p>
                    <p>If you received this, your SMTP configuration is working correctly.</p>
                </body>
            </html>
            """

            message.attach(MIMEText(text_content, "plain"))
            message.attach(MIMEText(html_content, "html"))

            # Send the email
            self._send_email(smtp_config, address, message)

            logger.info(f"Test email sent successfully to {address}")
            return ProviderTestResponse(success=True, message="Test email sent successfully")

        except Exception as e:
            logger.error(f"Exception during SMTP email test: {e}")
            return ProviderTestResponse(success=False, message=f"Exception during test: {str(e)}")

    def _send_email(
        self, config: SMTPConfiguration, recipient: str, message: MIMEMultipart
    ) -> None:
        """Send email using SMTP."""
        context = ssl.create_default_context()

        if config.useSsl:
            # Use SSL from the start (usually port 465)
            with smtplib.SMTP_SSL(
                config.host, config.port, context=context, timeout=config.timeout
            ) as server:
                server.login(config.username, config.password)
                server.sendmail(config.fromEmail, recipient, message.as_string())
        else:
            # Use STARTTLS (usually port 587)
            with smtplib.SMTP(config.host, config.port, timeout=config.timeout) as server:
                if config.useTls:
                    server.starttls(context=context)
                server.login(config.username, config.password)
                server.sendmail(config.fromEmail, recipient, message.as_string())

    async def _send_per_request_callback(
        self,
        callback_url: Optional[str],
        callback_headers: Optional[Dict[str, str]],
        idempotency_key: str,
        status: str,
        recipient: str,
        notification_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Send callback to per-request callback URL.
        
        Args:
            callback_url: The callback URL from the request
            callback_headers: Optional headers for the callback
            idempotency_key: Original idempotency key
            status: Status of the notification ("sent", "failed")
            recipient: Recipient email address
            notification_id: Optional notification ID
            error_message: Optional error message for failures
        """
        if not callback_url:
            return
        
        if not self.webhook_client:
            logger.warning("WebhookClient not configured, skipping per-request callback")
            return
        
        try:
            payload = NotificationCallbackPayload(
                idempotencyKey=idempotency_key,
                status=status,
                channel="email",
                recipient=recipient,
                timestamp=datetime.utcnow(),
                notificationId=notification_id,
                errorMessage=error_message
            )
            
            logger.info(f"Sending per-request callback to {callback_url} for {recipient}: status={status}")
            
            # Send callback in fire-and-forget manner (don't block the response)
            asyncio.create_task(
                self.webhook_client.send_callback(
                    callback_url=callback_url,
                    payload=payload,
                    headers=callback_headers,
                    max_retries=3,
                    base_delay=1.0
                )
            )
            
        except Exception as e:
            logger.error(f"Error sending per-request callback to {callback_url}: {e}", exc_info=True)

    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantEmailConfiguration,
        messageToSend: Dict[str, Any],
        templateId: UUID,
        saveToOutbox: bool = True
    ) -> NotificationResponse:
        """
        Send Email via SMTP.
        Loads configuration from database (tenantConfig.config).

        Args:
            requestObject: The notification request
            tenantConfig: Tenant email configuration
            messageToSend: Dictionary containing subject, body, bodyType
            templateId: Template ID for tracking
            saveToOutbox: If True, save failed messages to outbox for retry (fire-and-forget mode).
                         If False, just return failure (immediate mode, caller handles retry).
        """
        try:
            # Load configuration from database (tenantConfig.config)
            smtp_config = SMTPConfiguration.fromDict(tenantConfig.config)

            # Get recipient address
            address = requestObject.recipient.address

            if not address:
                return NotificationResponse(
                    success=False,
                    message="No recipient provided",
                )

            isAllSent: bool = True
            notificationResponsePerRecipient: List[NotifiationResponsePerRecipient] = []

           
            try:
                    # Create email message
                    message = MIMEMultipart("alternative")
                    message["Subject"] = messageToSend.get("subject", "Notification")
                    message["From"] = (
                        f"{smtp_config.fromName} <{smtp_config.fromEmail}>"
                        if smtp_config.fromName
                        else smtp_config.fromEmail
                    )
                    message["To"] = address

                    # Get body content
                    body = messageToSend.get("body", "")
                    bodyType = messageToSend.get("bodyType", "html")

                    # Create message content based on body type
                    if bodyType == "html":
                        # Add both plain text fallback and HTML
                        # Simple HTML to text conversion for fallback
                        import re
                        plain_text = re.sub(r'<[^>]+>', '', body)
                        message.attach(MIMEText(plain_text, "plain"))
                        message.attach(MIMEText(body, "html"))
                    else:
                        message.attach(MIMEText(body, "plain"))

                    # Log information
                    logger.info(f"Sending email to {address}")
                    logger.info(f"Subject: {messageToSend.get('subject', 'Notification')}")
                    logger.info(f"From: {smtp_config.fromEmail}")

                    # Send the email
                    self._send_email(smtp_config, address, message)

                    # Save successful notification
                    emailNotification = EmailNotification(
                        id=uuid.uuid4(),
                        recipientEmail=address,
                        messageContent=messageToSend,
                        templateId=templateId,
                        status=NotificationStatus.SENT,
                        idempotencyKey=requestObject.idempotencyKey,
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow(),
                    )
                    try:
                        async with self.uow:
                            await self.uow.emailNotifications.add(emailNotification)
                    except Exception as save_exc:
                        logger.error(
                            f"Failed to save email notification for {address}: {save_exc}",
                            exc_info=True,
                        )

                    notificationResponse = NotifiationResponsePerRecipient(
                        notificationId=str(emailNotification.id),
                        status=NotificationStatus.SENT,
                        recipient=address,
                        createdAt=emailNotification.createdAt,
                        success=True,
                        message="Email sent successfully",
                    )
                    notificationResponsePerRecipient.append(notificationResponse)
                    
                    # Send per-request callback for successful delivery
                    await self._send_per_request_callback(
                        callback_url=requestObject.callbackUrl,
                        callback_headers=requestObject.callbackHeaders,
                        idempotency_key=requestObject.idempotencyKey,
                        status="sent",
                        recipient=address,
                        notification_id=str(emailNotification.id)
                    )

            except Exception as exc:
                    error_message = f"{type(exc).__name__}: {str(exc) or 'No error details (SMTP provider)'}"
                    logger.error(f"Error sending email to {address} via SMTP: {error_message}", exc_info=True)

                    # Only save to outbox if saveToOutbox is True (fire-and-forget mode)
                    if saveToOutbox:
                        emailOutbox = EmailOutbox(
                            id=uuid.uuid4(),
                            recipientEmail=address,
                            messageContent=messageToSend,
                            idempotencyKey=requestObject.idempotencyKey,
                            templateId=templateId,
                            retryCount=0,
                            status="failed",
                            lastErrorMessage=error_message,
                            providerAttempted="smtp",
                            callbackUrl=requestObject.callbackUrl,
                            callbackHeaders=requestObject.callbackHeaders,
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow(),
                        )
                        try:
                            async with self.uow:
                                await self.uow.emailOutbox.add(emailOutbox)
                        except Exception as save_exc:
                            save_error = f"{type(save_exc).__name__}: {str(save_exc)}"
                            logger.error(
                                f"Failed to save email outbox for {address}: {save_error}",
                                exc_info=True,
                            )

                        notificationResponsePerRecipient.append(
                            NotifiationResponsePerRecipient(
                                notificationId=str(emailOutbox.id),
                                status="failed",
                                recipient=address,
                                createdAt=emailOutbox.createdAt,
                                success=False,
                                errorMessage=str(exc),
                            )
                        )
                    else:
                        # Immediate mode - just return failure, caller handles retry
                        notificationResponsePerRecipient.append(
                            NotifiationResponsePerRecipient(
                                notificationId=None,
                                status="failed",
                                recipient=address,
                                createdAt=datetime.utcnow(),
                                success=False,
                                errorMessage=str(exc),
                            )
                        )
                        
                        # Send per-request callback for failed delivery (immediate mode only)
                        await self._send_per_request_callback(
                            callback_url=requestObject.callbackUrl,
                            callback_headers=requestObject.callbackHeaders,
                            idempotency_key=requestObject.idempotencyKey,
                            status="failed",
                            recipient=address,
                            error_message=str(exc)
                        )
                    isAllSent = False

            return NotificationResponse(
                success=isAllSent,
                message="Processing completed" if isAllSent else "Some messages failed to send",
                recipientResponse=notificationResponsePerRecipient,
            )

        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}", exc_info=True)
            return NotificationResponse(
                success=False, errorMessage=f"Error sending email via SMTP: {str(e)}"
            )

    async def send_raw(
        self,
        recipient: str,
        messageContent: Dict[str, Any],
        tenantConfig: TenantEmailConfiguration
    ) -> tuple[bool, Optional[str]]:
        """
        Send a raw email message (used for outbox retry).
        
        Args:
            recipient: Email address to send to
            messageContent: Dictionary containing subject, body, bodyType
            tenantConfig: Tenant email configuration with provider credentials
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            smtp_config = SMTPConfiguration.fromDict(tenantConfig.config)
            
            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = messageContent.get("subject", "Notification")
            message["From"] = (
                f"{smtp_config.fromName} <{smtp_config.fromEmail}>"
                if smtp_config.fromName
                else smtp_config.fromEmail
            )
            message["To"] = recipient
            
            # Get body content
            body = messageContent.get("body", "")
            bodyType = messageContent.get("bodyType", "html")
            
            # Create message content based on body type
            if bodyType == "html":
                import re
                plain_text = re.sub(r'<[^>]+>', '', body)
                message.attach(MIMEText(plain_text, "plain"))
                message.attach(MIMEText(body, "html"))
            else:
                message.attach(MIMEText(body, "plain"))
            
            # Send the email
            self._send_email(smtp_config, recipient, message)
            
            logger.info(f"Email sent successfully to {recipient} via SMTP (retry)")
            return (True, None)
            
        except Exception as e:
            logger.error(f"Exception sending email to {recipient} via SMTP: {e}")
            return (False, str(e))