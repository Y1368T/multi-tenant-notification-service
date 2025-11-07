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
        request_object: NotificationRequest,
        tenant_config: TenantSMSConfiguration,
        message_to_send: str,
        template_id: UUID
    ) -> NotificationResponse:
        """
        Send SMS via EthioTelecom shortcode API.
        """
        # TODO: Implement actual EthioTelecom API call
        # This is a placeholder implementation
        
        try:
            # Simulate API call
            provider_message_id = str(uuid.uuid4())
            addresses = [recipient.address for recipient in request_object.recipients]
            
            
            logger.info(f"Sent SMS to {addresses} with message {message_to_send}, provider_message_id: {provider_message_id}")
            #send a callback request
            callback=tenant_config.config.get("callback_url")
            if callback:
                #simulate callback
                callback_data={
                    "notification_id":provider_message_id,
                    "status":"DELIVERED",
                    "delivered_at":datetime.utcnow().isoformat()+"Z"
                }
                logger.info(f"Sending callback to {callback} with data {callback_data}")
                afro_response=  await self.send_afro_message(addresses,message_to_send)
            return NotificationResponse(
                notification_id=provider_message_id,
                status="sent",
                channel="SMS",
                recipients=addresses,
                tenant_id=str(tenant_config.tenant_id),
                created_at=datetime.utcnow(),
                success=True,
                message=message_to_send
            )
        except Exception as e:
            return NotificationResponse(  
                notification_id="",
                status="failed",
                channel="SMS",
                recipients=[],
                tenant_id=str(tenant_config.tenant_id),
                created_at=datetime.utcnow(),
                success=False,
                message=str(e)
            )

    async def callback(
        self,
        provider_callback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process EthioTelecom delivery status callback.
        """
        # Map EthioTelecom status to normalized status
        status_mapping = {
            "DELIVERED": "delivered",
            "FAILED": "failed",
            "PENDING": "sent"
        }
        
        return {
            "notification_id": provider_callback.get("notification_id"),
            "status": status_mapping.get(provider_callback.get("status"), "unknown"),
            "delivered_at": provider_callback.get("delivered_at"),
            "error_message": provider_callback.get("error_message")
        }
    
    async def save_to_outbox(
        self,
        notification_id: str,
        request_object: Dict[str, Any],
        retry_count: int = 0,
        next_retry_at: Any = None
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
    
    async def send_afro_message(self,address:list[str],message:str):
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
    