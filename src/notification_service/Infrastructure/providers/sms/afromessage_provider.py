from typing import Any, Dict
from notification_service.domain.interfaces.iprovider_service import IProviderService
import uuid
from datetime import datetime
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.notification_response import NotificationResponse, ProviderTestResponse
from notification_service.domain.value_objects.notification_request import NotificationRequest
from uuid import UUID
import logging
import httpx
from pydantic import BaseModel

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
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseUrl": self.baseUrl,
            "apiKey": self.apiKey,
            "sender": self.sender,
            "from": self.from_,
            "callbackUrl": self.callbackUrl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AfromessageConfiguration':
        return cls(
            baseUrl=data.get("baseUrl", "https://api.afromessage.com/api"),
            apiKey=data.get("apiKey", ""),
            sender=data.get("sender", ""),
            from_=data.get("from") or data.get("from_", ""),
            callbackUrl=data.get("callbackUrl", "")
        )


class AfromessageSMSProvider(IProviderService):
    """Afromessage SMS provider implementation."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        """Test Afromessage configuration by sending a test message."""
        try:
            afro_config = AfromessageConfiguration.from_dict(config)
            url = f"{afro_config.baseUrl}/send"
            
            payload = {
                "from": afro_config.from_,
                "sender": afro_config.sender,
                "to": address,
                "message": "This is a test message from notification service"
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
        templateId: UUID
    ) -> NotificationResponse:
        """
        Send SMS via Afromessage API.
        Loads configuration from database (tenantConfig.config) instead of environment variables.
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
            
            # Send to each recipient
            successful_recipients = []
            failed_recipients = []
            provider_message_id = None
            
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
                    provider_message_id = response_data.get("id") or str(uuid.uuid4())
                    
                    successful_recipients.append(address)
                    logger.info(f"SMS sent successfully to {address}, response: {response_data}")
                    
                except Exception as e:
                    failed_recipients.append(address)
                    logger.error(f"Failed to send SMS to {address}: {e}")
            
            # Return response based on results
            if successful_recipients:
                return NotificationResponse(
                    notificationId=provider_message_id or str(uuid.uuid4()),
                    status="sent",
                    channel="SMS",
                    recipients=successful_recipients,
                    tenantId=str(tenantConfig.tenantId),
                    createdAt=datetime.utcnow(),
                    success=True,
                    message=messageToSend
                )
            else:
                return NotificationResponse(
                    notificationId="",
                    status="failed",
                    channel="SMS",
                    recipients=[],
                    tenantId=str(tenantConfig.tenantId),
                    createdAt=datetime.utcnow(),
                    success=False,
                    message=f"Failed to send to all recipients: {', '.join(failed_recipients)}"
                )
                
        except Exception as e:
            logger.error(f"Error sending SMS via Afromessage: {e}", exc_info=True)
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
        Process Afromessage delivery status callback.
        """
        # Map Afromessage status to normalized status
        status_mapping = {
            "DELIVERED": "delivered",
            "FAILED": "failed",
            "PENDING": "sent",
            "SENT": "sent"
        }
        
        return {
            "notificationId": providerCallback.get("notificationId") or providerCallback.get("id"),
            "status": status_mapping.get(providerCallback.get("status", "").upper(), "unknown"),
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
        pass
    
    async def circuit_breaker_check(
        self,
        config: TenantSMSConfiguration
    ) -> bool:
        """
        Perform circuit breaker check for Afromessage SMS provider.
        """
        # Implement circuit breaker logic here
        return True

