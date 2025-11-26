from notification_service.domain.interfaces.iprovider_service import IProviderService
from typing import Dict,Any
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from uuid import UUID
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
                
                smsNotification=SMSNotification(
                    id=uuid.uuid4(),
                    recipientNumber=recipient.address,
                    messageContent=requestObject.payload,
                    status=NotificationStatus.SENT,
                    idempotencyKey = requestObject.idempotencyKey,
                    templateId=templateId
                )
                # You might want to save smsNotification to a database or log it here
                result=await self.uow.smsNotifications.add(smsNotification)
                await self.uow.commit()
                logger.info(f"SMSNotification saved with ID: {result.id}")
                return NotificationResponse(
                    notificationId=str(uuid.uuid4()),
                    tenantId=tenantConfig.tenantId,
                    channel="sms",
                    recipients=[recipient.address],
                    status="sent",
                    createdAt=datetime.utcnow(),
                    success=True, 
                    message=f"SMS sent successfully to {recipient.address}")
            elif response.error:
                logger.error(f"Failed to send SMS to {recipient.address}: {response.error}")
                payloadStr = json.dumps(requestObject.payload) if isinstance(requestObject.payload, dict) else str(requestObject.payload)
                outbox=SMSOutbox (
                    id=uuid.uuid4(),
                    recipientNumber=recipient.address,
                    messageContent=payloadStr,
                    idempotencyKey=requestObject.idempotencyKey,
                    templateId=templateId,
                    retryCount=1,
                    nextRetryAt=None,
                    lastRetryAt=None,
                    providerAttempted=SMSProvider.KIFIYA.value,
                    
                         )
                await self.uow.smsOutbox.add(outbox)
                return NotificationResponse(success=False,message="Saved to outbox",notificationId=outbox.id,status="saved_to_outbox")
            return NotificationResponse(success=False,message="Failed to send message")
    
    
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
            
    
    async def callback(self, providerCallback):
        return await super().callback(providerCallback)
    
    async def saveToOutbox(self, notificationId, requestObject, retryCount = 0, nextRetryAt = None):
        return await super().saveToOutbox(notificationId, requestObject, retryCount, nextRetryAt)
        