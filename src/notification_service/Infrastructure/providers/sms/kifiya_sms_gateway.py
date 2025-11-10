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
    def from_dict(cls, data: Dict[str, Any]) -> 'KifiyaSMSConfig':
        return cls(
            tokenId=data.get("tokenId", ""),
            url=data.get("url", "")
        )
    def to_dict(self):
        return {
            "tokenId": self.tokenId,
            "url": self.url
        }
    
class KifiyaSMSGateway(IProviderService):
    def __init__(self, uow:IUnitOfWork):
        self.uow = uow
        self.client = httpx.AsyncClient(timeout=30.0)
        pass
    
    async def send(
        self,
        request_object: NotificationRequest,
        tenant_config: TenantSMSConfiguration,
        message_to_send: str,
        template_id: UUID
    ) -> NotificationResponse:
        # TODO: Implement actual Kifiya SMS Gateway API call
        logger.info("Sending SMS via Kifiya SMS Gateway")
        
        config=KifiyaSMSConfig.from_dict(tenant_config.config)
        for recipient in request_object.recipients:
            payload={
                "tokenId": config.tokenId,
                "phoneNo": recipient.address ,
                "message": message_to_send
            }
            
            
            response_data= await self.client.post(
                config.url,
                json=payload
            )
            logger.info(f"Response from Kifiya SMS Gateway: {response_data.json()}")
            response = KifiyaSMSResponse(**response_data.json())
            if response.status=="success":
                logger.info(f"SMS sent successfully to {recipient.address}")
                
                sms_notification=SMSNotification(
                    id=uuid.uuid4(),
                    recipient_number=recipient.address,
                    message_content=request_object.payload,
                    status=NotificationStatus.SENT,
                    idempotency_key = request_object.idempotency_key,
                    template_id=template_id
                )
                # You might want to save sms_notification to a database or log it here
                result=await self.uow.sms_notifications.add(sms_notification)
                await self.uow.commit()
                logger.info(f"SMSNotification saved with ID: {result.id}")
                return NotificationResponse(
                    notification_id=str(uuid.uuid4()),
                    tenant_id=tenant_config.tenant_id,
                    channel="sms",
                    recipients=[recipient.address],
                    status="sent",
                    created_at=datetime.utcnow(),
                    success=True, 
                    message=f"SMS sent successfully to {recipient.address}")
            elif response.error:
                logger.error(f"Failed to send SMS to {recipient.address}: {response.error}")
                payload_str = json.dumps(request_object.payload) if isinstance(request_object.payload, dict) else str(request_object.payload)
                outbox=SMSOutbox (
                    id=uuid.uuid4(),
                    recipient_number=recipient.address,
                    message_content=payload_str,
                    idempotency_key=request_object.idempotency_key,
                    template_id=template_id,
                    retry_count=1,
                    next_retry_at=None,
                    last_retry_at=None,
                    provider_attempted=SMSProvider.KIFIYA.value,
                    
                         )
                await self.uow.sms_outbox.add(outbox)
                return NotificationResponse(success=False,message="Saved to outbox",notification_id=outbox.id,status="saved_to_outbox")
            return NotificationResponse(success=False,message="Failed to send message")
    
    
    async def test(self, config: Dict[str, Any],address:str) -> ProviderTestResponse:
            try:   
                kifiyasmsconf=KifiyaSMSConfig.from_dict(config)
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
            
    
    async def callback(self, provider_callback):
        return await super().callback(provider_callback)
    
    async def save_to_outbox(self, notification_id, request_object, retry_count = 0, next_retry_at = None):
        return await super().save_to_outbox(notification_id, request_object, retry_count, next_retry_at)
        