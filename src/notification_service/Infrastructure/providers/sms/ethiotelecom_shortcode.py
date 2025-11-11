from typing import Any, Dict, List
from notification_service.domain.interfaces.iprovider_service import IProviderService
import uuid
from datetime import datetime
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.value_objects.notification_request import NotificationRequest
from uuid import UUID
import logging
import os
import requests
from pydantic import BaseModel
logger = logging.getLogger(__name__)
class EthioTelecomConfiguration(BaseModel):
    """Configuration settings for EthioTelecom shortcode SMS provider."""
    shortcode: str
    service_id: str
    api_key: str
    api_secret: str
    callback_url: str = ""
    
    class Config:
        from_attributes = True
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shortcode": self.shortcode,
            "service_id": self.service_id,
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "callback_url":self.callback_url
        }
    @classmethod
    def from_dict(cls,data: Dict[str, Any]) -> 'EthioTelecomConfiguration':
        return cls(
            shortcode=data["shortcode"],
            service_id=data["service_id"],
            api_key=data["api_key"],
            api_secret=data["api_secret"],
            callback_url=data.get("callback_url","")
        )
class EthioTelecomShortcodeSMSProvider(IProviderService):
   
    def __init__(self):
        pass
     
    async def test(self, config: Dict[str, Any],address:str) -> bool:
        pass

    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
        templateId: UUID
    ) -> NotificationResponse:
        """
        Send SMS via EthioTelecom shortcode API.
        """
        # TODO: Implement actual EthioTelecom API call
        # This is a placeholder implementation
        
        try:
            # Simulate API call
            providerMessageId = str(uuid.uuid4())
            addresses = [recipient.address for recipient in requestObject.recipients]
            
            
            logger.info(f"Sent SMS to {addresses} with message {messageToSend}, providerMessageId: {providerMessageId}")
            #send a callback request
            callback=tenantConfig.config.get("callback_url")
            if callback:
                #simulate callback
                callbackData={
                    "notificationId":providerMessageId,
                    "status":"DELIVERED",
                    "deliveredAt":datetime.utcnow().isoformat()+"Z"
                }
                logger.info(f"Sending callback to {callback} with data {callbackData}")
                afroResponse=  await self.sendAfroMessage(addresses,messageToSend)
            return NotificationResponse(
                notificationId=providerMessageId,
                status="sent",
                channel="SMS",
                recipients=addresses,
                tenantId=str(tenantConfig.tenantId),
                createdAt=datetime.utcnow(),
                success=True,
                message=messageToSend
            )
        except Exception as e:
            return NotificationResponse(  
                notificationId="",
                status="failed",
                channel="SMS",
                recipients=[],
                tenantId=str(tenantConfig.tenantId),
                createdAt=datetime.utcnow(),
                success=False,
                message=str(e)
            )

    async def callback(
        self,
        providerCallback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process EthioTelecom delivery status callback.
        """
        # Map EthioTelecom status to normalized status
        statusMapping = {
            "DELIVERED": "delivered",
            "FAILED": "failed",
            "PENDING": "sent"
        }
        
        return {
            "notificationId": providerCallback.get("notificationId") or providerCallback.get("notification_id"),
            "status": statusMapping.get(providerCallback.get("status"), "unknown"),
            "deliveredAt": providerCallback.get("deliveredAt") or providerCallback.get("delivered_at"),
            "errorMessage": providerCallback.get("errorMessage") or providerCallback.get("error_message")
        }
    
    async def saveToOutbox(
        self,
        notificationId: str,
        requestObject: Dict[str, Any],
        retryCount: int = 0,
        nextRetryAt: Any = None
    ) -> None:
        """
        Save notification to outbox for guaranteed delivery.
        """
        # TODO: Implement actual outbox persistence
        # This would typically save to a database table
        pass
    async def circuit_breaker_check(
        self,
        config: TenantSMSConfiguration
    ) -> bool:
        """
        Perform circuit breaker check for EthioTelecom shortcode SMS provider.
        """
        # Implement circuit breaker logic here
        return True
    
    async def sendAfroMessage(self,address:list[str],message:str):
            base_url = os.getenv("AFROMESSAGE_BASEURL", "https://api.afromessage.com/api")
            token = os.getenv("AFROMESSAGE_APIKEY", "")
            url = f"{base_url}/send"
            callback_url = os.getenv("AFROMESSAGE_CALLBACKURL", "https://db24-196-188-34-81.ngrok-free.app/api/SMS/delivered")
            
            # Append notification ID to callback URL
            
            
            # Construct payload
            payload = {
                "from": os.getenv("AFROMESSAGE_FROM", "e80ad9d8-adf3-463f-80f4-7c4b39f7f164"),
                "sender": os.getenv("AFROMESSAGE_SENDER", "TRUCKSLOAD"),
                "to": address[0],
                "message": message,
                "callback": callback_url
            }
            
            # Log information
            logger.info(f"Sending SMS to {address[0]} with content: {message}")
            logger.info(f"Base URL: {os.getenv('AFROMESSAGE_BASEURL')}")
            logger.info(f"API Key: {os.getenv('AFROMESSAGE_APIKEY')}")
            logger.info(f"Sender Name: {os.getenv('AFROMESSAGE_SENDER')}")
            logger.info(f"From: {os.getenv('AFROMESSAGE_FROM')}")
            
            # Prepare HTTP request
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Send request
            response = requests.post(url, json=payload, headers=headers)
            logger.info(f"Response status code: {response.status_code}")
            return response
    