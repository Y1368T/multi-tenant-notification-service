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
        templateId: UUID
    ) -> NotificationResponse:
        # TODO: Implement actual Kifiya SMS Gateway API call
        logger.info("Sending SMS via Kifiya SMS Gateway")
        
        config=KifiyaSMSConfig.fromDict(tenantConfig.config)
        notificationResponsePerRecipient: List[NotifiationResponsePerRecipient]=[]
        isAllSent:bool=True
        for recipient in requestObject.recipients:
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
                        status=NotificationStatus.SENT.value,
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
                        updatedAt=smsnotification.updatedAt,
                        success=True,
                        message="SMS sent successfully"
                    )
                    notificationResponsePerRecipient.append(notifcationResponse)
                    isAllSent = True
            elif response.error:
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
                    logger.error(f"Failed to send SMS via Jasmin HTTP to {recipient.address}, response: {response.error}")
                    notifcationResponse=NotifiationResponsePerRecipient(
                        notificationId=str(smsOutBox.id),
                        status="failed",
                        recipient=recipient.address,
                        createdAt=smsOutBox.createdAt,
                        updatedAt=smsOutBox.updatedAt,
                        success=False,
                        message="Saved to outbox for retrying later",
                        errorMessage=response.error,
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
            
    
    