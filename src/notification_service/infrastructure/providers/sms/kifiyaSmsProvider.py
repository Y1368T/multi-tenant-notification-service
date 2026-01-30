from notification_service.domain.interfaces.iprovider_service import IProviderService
from typing import Dict,Any, List
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotifiationResponsePerRecipient, NotificationResponse
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from uuid import UUID, uuid4
from datetime import datetime
import uuid
import requests
from pydantic import BaseModel
from typing import Optional
import logging
import httpx
import json

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
    def __init__(self, uow:IUnitOfWork):
        self.uow = uow
        self.client = httpx.AsyncClient(timeout=30.0)
        pass
    
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
                    "phoneNo": recipient.address ,
                    "message": messageToSend
                }
                
                
                responseData= await self.client.post(
                    config.url,
                    json=payload
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
                        providerAttempted="kifiya"
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
                payload={
                    "tokenId": kifiyasmsconf.tokenId,
                    "phoneNo": address ,
                    "message": "This is a test message"
                }
                response_data= await self.client.post(
                    kifiyasmsconf.url,
                    json=payload
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
            
            response_data = await self.client.post(config.url, json=payload)
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
    