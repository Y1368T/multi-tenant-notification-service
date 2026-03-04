import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING

import httpx
from pydantic import BaseModel

from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotifiationResponsePerRecipient, NotificationResponse
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from notification_service.infrastructure.services.webhook_client import WebhookClient

logger = logging.getLogger(__name__)

class KifiyaSMSResponse(BaseModel):
    status: Optional[str]=None
    message: Optional[str]=None
    phoneNo:Optional[str]=None
    error:Optional[str]=None
    
class KifiyaSMSConfig(BaseModel):
    tokenId: str
    url:str
    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> 'KifiyaSMSConfig':
        return cls(
            tokenId=data.get("tokenId", ""),
            url=data.get("url", "")
        )
    def toDict(self):
        return {
            "tokenId": self.tokenId,
            "url": self.url
        }
    
class KifiyaSMSProvider(IProviderService):
    def __init__(self, uow: IUnitOfWork, webhook_client: "WebhookClient" = None):
        self.uow = uow
        # Set default headers with UTF-8 charset for Amharic/Unicode support
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json; charset=utf-8"
            }
        )
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
    
    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
        templateId: UUID,
        saveToOutbox: bool = True
    ) -> NotificationResponse:
        # TODO: Implement actual Kifiya SMS Gateway API call
        logger.info(f"Sending SMS via Kifiya SMS Gateway (saveToOutbox={saveToOutbox})")
        
        config=KifiyaSMSConfig.fromDict(tenantConfig.config)
        notificationResponsePerRecipient: List[NotifiationResponsePerRecipient]=[]
        isAllSent:bool=True
        for recipient in requestObject.recipients:
            try:
                payload={
                    "tokenId": config.tokenId,
                    "phoneNo": recipient.address,
                    "message": messageToSend
                }
                
                # Log the message content (including Amharic characters)
                logger.info(f"Sending SMS to {recipient.address}")
                logger.info(f"Message content (raw): {messageToSend}")
                logger.info(f"Message content (repr): {repr(messageToSend)}")
                logger.info(f"Payload JSON: {json.dumps(payload, ensure_ascii=False)}")
                
                # Use content with explicit UTF-8 encoding for Amharic/Unicode support
                # json=payload auto-serializes but may not preserve Unicode properly
                responseData = await self.client.post(
                    config.url,
                    content=json.dumps(payload, ensure_ascii=False).encode('utf-8')
                )
                logger.info(f"Response from Kifiya SMS Gateway: {responseData.json()}")
                response = KifiyaSMSResponse(**responseData.json())
                if response.status=="success":
                        logger.info(f"SMS sent successfully to {recipient.address}")
                    
                        smsnotification=SMSNotification(
                            id=uuid4(),
                            recipientNumber=recipient.address,
                            messageContent=messageToSend,
                            templateId=templateId,
                            status=NotificationStatus.SENT,
                            idempotencyKey=requestObject.idempotencyKey,
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow()
                        )
                        await self.uow.smsNotifications.add(smsnotification)
                        await self.uow.commit()
                        notifcationResponse=NotifiationResponsePerRecipient(
                            notificationId=str(smsnotification.id),
                            status="sent",
                            recipient=recipient.address,
                            createdAt=smsnotification.createdAt,
                            success=True,
                            message="SMS sent successfully"
                        )
                        notificationResponsePerRecipient.append(notifcationResponse)
                        isAllSent = True
                        
                        # Send callback on success (if callbackUrl provided)
                        await self._send_callback(
                            callback_url=requestObject.callbackUrl,
                            callback_headers=requestObject.callbackHeaders,
                            idempotency_key=requestObject.idempotencyKey,
                            status="sent",
                            recipient=recipient.address,
                            notification_id=str(smsnotification.id)
                        )
                elif response.error:
                        # Only save to outbox if saveToOutbox is True (fire-and-forget mode)
                        if saveToOutbox:
                            smsOutBox=SMSOutbox(
                                id=uuid4(),
                                recipientNumber=recipient.address,
                                messageContent=messageToSend,
                                idempotencyKey=requestObject.idempotencyKey,
                                templateId=templateId,
                                retryCount=0,
                                status="failed",
                                lastErrorMessage=response.error,
                                providerAttempted="kifiya",
                                callbackUrl=requestObject.callbackUrl,
                                callbackHeaders=requestObject.callbackHeaders,
                                createdAt=datetime.utcnow(),
                                updatedAt=datetime.utcnow()
                            )
                            await self.uow.smsOutboxes.add(smsOutBox)
                            await self.uow.commit()
                            logger.error(f"Failed to send SMS via Kifiya to {recipient.address}, saved to outbox: {response.error}")
                            notifcationResponse=NotifiationResponsePerRecipient(
                                notificationId=str(smsOutBox.id),
                                status="failed",
                                recipient=recipient.address,
                                createdAt=smsOutBox.createdAt,
                                success=False,
                                message="Saved to outbox for retrying later",
                                errorMessage=response.error,
                            )
                        else:
                            # Immediate mode - just return failure, caller handles retry
                            logger.error(f"Failed to send SMS via Kifiya to {recipient.address}: {response.error}")
                            notifcationResponse=NotifiationResponsePerRecipient(
                                notificationId=None,
                                status="failed",
                                recipient=recipient.address,
                                createdAt=datetime.utcnow(),
                                success=False,
                                message="Failed to send SMS",
                                errorMessage=response.error,
                            )
                        notificationResponsePerRecipient.append(notifcationResponse)
                        isAllSent = False
            except Exception as exc:
                # Handle connection errors, timeouts, etc.
                logger.error(f"Error sending SMS via Kifiya to {recipient.address}: {exc}")
                
                if saveToOutbox:
                    # Fire-and-forget mode: save to outbox for retry
                    smsOutBox=SMSOutbox(
                        id=uuid4(),
                        recipientNumber=recipient.address,
                        messageContent=messageToSend,
                        idempotencyKey=requestObject.idempotencyKey,
                        templateId=templateId,
                        retryCount=0,
                        status="pending",
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow(),
                        lastErrorMessage=str(exc),
                        providerAttempted="kifiya",
                        callbackUrl=requestObject.callbackUrl,
                        callbackHeaders=requestObject.callbackHeaders
                    )
                    await self.uow.smsOutboxes.add(smsOutBox)
                    await self.uow.commit()
                    logger.info(f"Saved failed SMS to outbox for {recipient.address}, outbox_id={smsOutBox.id}")
                    notifcationResponse=NotifiationResponsePerRecipient(
                        notificationId=str(smsOutBox.id),
                        status="pending",
                        recipient=recipient.address,
                        createdAt=smsOutBox.createdAt,
                        success=False,
                        message="Saved to outbox for retrying later",
                        errorMessage=str(exc),
                    )
                else:
                    # Immediate mode: just return failure, caller handles retry
                    logger.warning(f"Immediate mode: returning failure for {recipient.address}, caller should retry")
                    notifcationResponse=NotifiationResponsePerRecipient(
                        notificationId=None,
                        status="failed",
                        recipient=recipient.address,
                        createdAt=datetime.utcnow(),
                        success=False,
                        message="Failed to send SMS - connection error",
                        errorMessage=str(exc),
                    )
                notificationResponsePerRecipient.append(notifcationResponse)
                isAllSent = False
        return NotificationResponse(success=isAllSent,message="Processing completed" if isAllSent else "Some messages failed to send",recipientResponse=notificationResponsePerRecipient)
    
    
    async def test(self, config: Dict[str, Any],address:str) -> ProviderTestResponse:
            try:   
                kifiyasmsconf=KifiyaSMSConfig.fromDict(config)
                test_message = "This is a test message / የሙከራ መልእክት"  # Include Amharic for testing
                payload={
                    "tokenId": kifiyasmsconf.tokenId,
                    "phoneNo": address,
                    "message": test_message
                }
                
                # Log the test message content (including Amharic characters)
                logger.info(f"[test] Sending test SMS to {address}")
                logger.info(f"[test] Message content (raw): {test_message}")
                logger.info(f"[test] Message content (repr): {repr(test_message)}")
                logger.info(f"[test] Payload JSON: {json.dumps(payload, ensure_ascii=False)}")
                
                # Use content with explicit UTF-8 encoding for Amharic/Unicode support
                response_data = await self.client.post(
                    kifiyasmsconf.url,
                    content=json.dumps(payload, ensure_ascii=False).encode('utf-8')
                )
                response = KifiyaSMSResponse(**response_data.json())
                if response.status=="success":
                    return ProviderTestResponse(success=True,message="Test SMS sent successfully")
                elif response.error:
                    return ProviderTestResponse(success=False,message=f"Failed to send test SMS: {response.error}")
            except Exception as e:
                logger.error(f"Exception during Kifiya SMS test: {e}")
                return ProviderTestResponse(success=False,message=f"Exception during test: {str(e)}")
    
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
            config = KifiyaSMSConfig.fromDict(tenantConfig.config)
            payload = {
                "tokenId": config.tokenId,
                "phoneNo": recipient,
                "message": message
            }
            
            # Log the message content (including Amharic characters) for retry
            logger.info(f"[send_raw] Sending SMS to {recipient}")
            logger.info(f"[send_raw] Message content (raw): {message}")
            logger.info(f"[send_raw] Message content (repr): {repr(message)}")
            logger.info(f"[send_raw] Payload JSON: {json.dumps(payload, ensure_ascii=False)}")
            
            # Use content with explicit UTF-8 encoding for Amharic/Unicode support
            response_data = await self.client.post(
                config.url,
                content=json.dumps(payload, ensure_ascii=False).encode('utf-8')
            )
            logger.info(f"Kifiya send_raw response for {recipient}: {response_data.json()}")
            response = KifiyaSMSResponse(**response_data.json())
            
            if response.status == "success":
                logger.info(f"SMS sent successfully to {recipient} via Kifiya (retry)")
                return (True, None)
            else:
                error_msg = response.error or "Unknown error from Kifiya"
                logger.error(f"Failed to send SMS to {recipient} via Kifiya: {error_msg}")
                return (False, error_msg)
                
        except Exception as e:
            logger.error(f"Exception sending SMS to {recipient} via Kifiya: {e}")
            return (False, str(e))
    