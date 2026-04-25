import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.notification_response import NotifiationResponsePerRecipient, NotificationResponse, ProviderTestResponse
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload
from notification_service.infrastructure.services.webhook_client import WebhookClient
from uuid import UUID

logger = logging.getLogger(__name__)


class AfromessageConfiguration(BaseModel):
    """Configuration settings for Afromessage SMS provider."""
    baseUrl: str
    apiKey: str
    sender: str
    from_: str  # 'from' is a Python keyword, so use 'from_'
    callbackUrl: str = ""
    
    class Config:
        from_attributes = True
        
    def toDict(self) -> Dict[str, Any]:
        return {
            "baseUrl": self.baseUrl,
            "apiKey": self.apiKey,
            "sender": self.sender,
            "from": self.from_,
            "callbackUrl": self.callbackUrl
        }
    
    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> 'AfromessageConfiguration':
        return cls(
            baseUrl=data.get("baseUrl", "https://api.afromessage.com/api"),
            apiKey=data.get("apiKey", ""),
            sender=data.get("sender", ""),
            from_=data.get("from") or data.get("from_", ""),
            callbackUrl=data.get("callbackUrl", "")
        )


class AfromessageSMSProvider(IProviderService):
    """Afromessage SMS provider implementation."""
    
    def __init__(self, uow: IUnitOfWork, webhook_client: WebhookClient):
        self.uow = uow
        self.client = httpx.AsyncClient(timeout=30.0)
        self.webhook_client = webhook_client

    async def _send_callback(
        self,
        callback_url: Optional[str],
        callback_headers: Optional[Dict[str, str]],
        idempotency_key: str,
        status: str,
        recipient: str,
        notification_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Send callback to the provided URL."""
        if not callback_url:
            return
        
        if not self.webhook_client:
            logger.warning("WebhookClient not configured, skipping callback")
            return
        
        try:
            payload = NotificationCallbackPayload(
                idempotencyKey=idempotency_key,
                status=status,
                channel="sms",
                recipient=recipient,
                timestamp=datetime.utcnow(),
                notificationId=notification_id,
                errorMessage=error_message
            )
            
            logger.info(f"Sending callback to {callback_url} for {recipient}: status={status}")
            
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
            logger.error(f"Error sending callback to {callback_url}: {e}", exc_info=True)
    
    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        """Test Afromessage configuration by sending a test message."""
        try:
            afro_config = AfromessageConfiguration.fromDict(config)
            url = f"{afro_config.baseUrl}/send"
            
            payload = {
                "from": afro_config.from_,
                "sender": afro_config.sender,
                "to": address,
                "message": "This is a test message / የሙከራ መልእክት"
            }
            
            headers = {
                "Authorization": f"Bearer {afro_config.apiKey}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Test SMS sent successfully to {address}")
            return ProviderTestResponse(success=True, message="Test SMS sent successfully")
        except Exception as e:
            logger.error(f"Exception during Afromessage SMS test: {e}")
            return ProviderTestResponse(success=False, message=f"Exception during test: {str(e)}")

    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
        templateId: UUID,
        saveToOutbox: bool = True
    ) -> NotificationResponse:
        """
        Send SMS via Afromessage API.
        Loads configuration from database (tenantConfig.config) instead of environment variables.
        
        Args:
            saveToOutbox: If True, save failed messages to outbox for retry (fire-and-forget mode).
                         If False, just return failure (immediate mode, caller handles retry).
        """
        try:
            # Load configuration from database (tenantConfig.config)
            afro_config = AfromessageConfiguration.from_dict(tenantConfig.config)
            
            # Get recipient addresses
            addresses = [recipient.address for recipient in requestObject.recipients]
            
            if not addresses:
                return NotificationResponse(
                    notificationId="",
                    status="failed",
                    channel="SMS",
                    recipients=[],
                    tenantId=str(tenantConfig.tenantId),
                    createdAt=datetime.utcnow(),
                    success=False,
                    message="No recipients provided"
                )
            
            # Construct API URL
            url = f"{afro_config.baseUrl}/send"
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {afro_config.apiKey}",
                "Content-Type": "application/json"
            }
            
            isAllSent: bool = False
            
            notificationResponsePerRecipient: List[NotifiationResponsePerRecipient]=[]
            
            for address in addresses:
                try:
                    # Construct payload
                    payload = {
                        "from": afro_config.from_,
                        "sender": afro_config.sender,
                        "to": address,
                        "message": messageToSend
                    }
                    
                    # Add callback URL if provided
                    if afro_config.callbackUrl:
                        payload["callback"] = afro_config.callbackUrl
                    
                    # Log information
                    logger.info(f"Sending SMS to {address} with content: {messageToSend}")
                    logger.info(f"Base URL: {afro_config.baseUrl}")
                    logger.info(f"Sender: {afro_config.sender}")
                    logger.info(f"From: {afro_config.from_}")
                    
                    # Send request
                    response = await self.client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    response_data = response.json()
                    
                    if(response_data.get("status") == "success"):
                        smsNotification = SMSNotification(
                            id=uuid.uuid4(),
                            recipientNumber=address,
                            messageContent=messageToSend,
                            templateId=templateId,
                            status=NotificationStatus.SENT,
                            idempotencyKey=requestObject.idempotencyKey,
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow()
                        )
                        await self.uow.smsNotifications.add(smsNotification)
                        await self.uow.commit()
                        notifcationResponse = NotifiationResponsePerRecipient(
                            notificationId=str(smsNotification.id),
                            status=NotificationStatus.SENT,
                            recipient=address,
                            createdAt=smsNotification.createdAt,
                            success=True,
                            message="SMS sent successfully"
                        )
                        isAllSent = True
                        notificationResponsePerRecipient.append(notifcationResponse)
                        
                        # Send callback on success (if callbackUrl provided)
                        await self._send_callback(
                            callback_url=requestObject.callbackUrl,
                            callback_headers=requestObject.callbackHeaders,
                            idempotency_key=requestObject.idempotencyKey,
                            status="sent",
                            recipient=address,
                            notification_id=str(smsNotification.id)
                        )
                    else:
                        # Only save to outbox if saveToOutbox is True (fire-and-forget mode)
                        if saveToOutbox:
                            smsOutBox = SMSOutbox(
                                id=uuid.uuid4(),
                                recipientNumber=address,
                                messageContent=messageToSend,
                                idempotencyKey=requestObject.idempotencyKey,
                                templateId=templateId,
                                retryCount=0,
                                status="failed",
                                lastErrorMessage=response_data.get("error", "Failed to send SMS"),
                                providerAttempted="afromessage",
                                callbackUrl=requestObject.callbackUrl,
                                callbackHeaders=requestObject.callbackHeaders,
                                createdAt=datetime.utcnow(),
                                updatedAt=datetime.utcnow()
                            )
                            await self.uow.smsOutboxes.add(smsOutBox)
                            await self.uow.commit()
                            notificationResponsePerRecipient.append(NotifiationResponsePerRecipient(
                                notificationId=str(smsOutBox.id),
                                status="failed",
                                recipient=address,
                                createdAt=smsOutBox.createdAt,
                                success=False,
                                errorMessage=response_data.get("error", "Failed to send SMS")
                            ))
                        else:
                            # Immediate mode - just return failure, caller handles retry
                            notificationResponsePerRecipient.append(NotifiationResponsePerRecipient(
                                notificationId=None,
                                status="failed",
                                recipient=address,
                                createdAt=datetime.utcnow(),
                                success=False,
                                errorMessage=response_data.get("error", "Failed to send SMS")
                            ))
                        isAllSent = False
                    
                except Exception as exc:
                    logger.error(f"Error sending SMS to {address} via Afromessage: {exc}", exc_info=True)
                    # Only save to outbox if saveToOutbox is True (fire-and-forget mode)
                    if saveToOutbox:
                        smsOutBox = SMSOutbox(
                            id=uuid.uuid4(),
                            recipientNumber=address,
                            messageContent=messageToSend,
                            idempotencyKey=requestObject.idempotencyKey,
                            templateId=templateId,
                            retryCount=0,
                            status="failed",
                            lastErrorMessage=str(exc),
                            providerAttempted="afromessage",
                            callbackUrl=requestObject.callbackUrl,
                            callbackHeaders=requestObject.callbackHeaders,
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow()
                        )
                        await self.uow.smsOutboxes.add(smsOutBox)
                        await self.uow.commit()
                        notificationResponsePerRecipient.append(NotifiationResponsePerRecipient(
                            notificationId=str(smsOutBox.id),
                            status="failed",
                            recipient=address,
                            createdAt=smsOutBox.createdAt,
                            success=False,
                            errorMessage=str(exc)
                        ))
                    else:
                        # Immediate mode - just return failure, caller handles retry
                        notificationResponsePerRecipient.append(NotifiationResponsePerRecipient(
                            notificationId=None,
                            status="failed",
                            recipient=address,
                            createdAt=datetime.utcnow(),
                            success=False,
                            errorMessage=str(exc)
                        ))
                    isAllSent = False
            # Return response based on results
            
            return NotificationResponse(
                    success=isAllSent,
                    message="Processing completed" if isAllSent else "Some messages failed to send",
                    recipientResponse=notificationResponsePerRecipient
                    
                )
                
        except Exception as e:
            logger.error(f"Error sending SMS via Afromessage: {e}", exc_info=True)
            return NotificationResponse(
                success=False,
                errorMessage=f"Error sending SMS via Afromessage: {str(e)}"
            )

    async def send_raw(
        self,
        recipient: str,
        message: str,
        tenantConfig: TenantSMSConfiguration
    ) -> tuple[bool, Optional[str]]:
        """
        Send a raw SMS message (used for outbox retry).
        
        Args:
            recipient: Phone number to send to
            message: Already-rendered message content
            tenantConfig: Tenant SMS configuration with provider credentials
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            afro_config = AfromessageConfiguration.fromDict(tenantConfig.config)
            url = f"{afro_config.baseUrl}/send"
            
            headers = {
                "Authorization": f"Bearer {afro_config.apiKey}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "from": afro_config.from_,
                "sender": afro_config.sender,
                "to": recipient,
                "message": message
            }
            
            if afro_config.callbackUrl:
                payload["callback"] = afro_config.callbackUrl
            
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            
            if response_data.get("status") == "success":
                logger.info(f"SMS sent successfully to {recipient} via Afromessage (retry)")
                return (True, None)
            else:
                error_msg = response_data.get("error", "Unknown error from Afromessage")
                logger.error(f"Failed to send SMS to {recipient} via Afromessage: {error_msg}")
                return (False, error_msg)
                
        except Exception as e:
            logger.error(f"Exception sending SMS to {recipient} via Afromessage: {e}")
            return (False, str(e))
