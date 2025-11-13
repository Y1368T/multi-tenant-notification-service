from notification_service.domain.interfaces.iprovider_service import IProviderService
from typing import Dict, Any
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.in_app.in_app_notification import InAppNotification
from notification_service.domain.value_objects.notification_status import NotificationStatus
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.providers import PushProvider
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from uuid import UUID
from datetime import datetime
import uuid
from pydantic import BaseModel
from typing import Optional, List
import logging
import httpx
import json

logger = logging.getLogger(__name__)

class FCMResponse(BaseModel):
    """FCM API response model"""
    success: Optional[bool] = None
    message_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

class FCMConfig(BaseModel):
    """FCM configuration model"""
    server_key: str
    project_id: str
    api_url: str = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FCMConfig':
        return cls(
            server_key=data.get("serverKey") or data.get("server_key", ""),
            project_id=data.get("projectId") or data.get("project_id", ""),
            api_url=data.get("apiUrl") or data.get("api_url", f"https://fcm.googleapis.com/v1/projects/{data.get('projectId', '')}/messages:send")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "serverKey": self.server_key,
            "projectId": self.project_id,
            "apiUrl": self.api_url
        }
    
    def get_api_url(self) -> str:
        """Get the full FCM API URL with project ID"""
        return self.api_url.format(project_id=self.project_id)

class FCMProvider(IProviderService):
    """Firebase Cloud Messaging (FCM) provider for in-app/push notifications"""
    
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: Any,  # TenantInAppConfiguration
        messageToSend: Dict[str, Any],  # FCM message payload
        templateId: UUID
    ) -> NotificationResponse:
        """
        Send in-app notification via FCM.
        
        Args:
            requestObject: Notification request
            tenantConfig: Tenant in-app configuration
            messageToSend: FCM message payload (dict with title, body, data, etc.)
            templateId: Template ID
            
        Returns:
            NotificationResponse with success status
        """
        logger.info("Sending in-app notification via FCM")
        
        config = FCMConfig.from_dict(tenantConfig.config)
        
        # Prepare FCM message for each recipient
        for recipient in requestObject.recipients:
            # FCM message structure
            fcm_message = {
                "message": {
                    "token": recipient.address,  # Device token
                    "notification": {
                        "title": messageToSend.get("title", "Notification"),
                        "body": messageToSend.get("body", "")
                    },
                    "data": messageToSend.get("data", {}),
                    "android": messageToSend.get("android", {}),
                    "apns": messageToSend.get("apns", {})
                }
            }
            
            try:
                # Send to FCM API
                # FCM v1 API uses OAuth2 access token, but for simplicity we'll use the legacy API
                # which uses server key in Authorization header
                fcm_url = f"https://fcm.googleapis.com/fcm/send"
                response_data = await self.client.post(
                    fcm_url,
                    json={
                        "to": recipient.address,  # Device token
                        "notification": fcm_message.get("notification", {}),
                        "data": fcm_message.get("data", {})
                    },
                    headers={
                        "Authorization": f"key={config.server_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                response_data.raise_for_status()
                response_json = response_data.json()
                
                logger.info(f"FCM response for {recipient.address}: {response_json}")
                
                # Check if message was sent successfully
                # Legacy FCM API returns success=1 and message_id on success
                if response_json.get("success") == 1 or response_json.get("message_id"):
                    logger.info(f"In-app notification sent successfully to {recipient.address}")
                    
                    # Save notification to database
                    in_app_notification = InAppNotification(
                        id=uuid.uuid4(),
                        recipientUserId=recipient.address,
                        messageContent=json.dumps(messageToSend) if isinstance(messageToSend, dict) else str(messageToSend),
                        status=NotificationStatus.SENT,
                        idempotencyKey=requestObject.idempotencyKey,
                        templateId=templateId
                    )
                    
                    result = await self.uow.inAppNotifications.add(in_app_notification)
                    await self.uow.commit()
                    logger.info(f"InAppNotification saved with ID: {result.id}")
                    
                    return NotificationResponse(
                        notificationId=str(result.id),
                        tenantId=tenantConfig.tenantId,
                        channel="in_app",
                        recipients=[recipient.address],
                        status="sent",
                        createdAt=datetime.utcnow(),
                        success=True,
                        message=f"In-app notification sent successfully to {recipient.address}"
                    )
                else:
                    # Handle FCM error response
                    error = response_json.get("error", {})
                    error_message = error.get("message", "Unknown FCM error")
                    logger.error(f"Failed to send FCM notification to {recipient.address}: {error_message}")
                    
                    # Save to outbox for retry (if outbox exists for in-app)
                    # For now, return error response
                    return NotificationResponse(
                        success=False,
                        message=f"Failed to send notification: {error_message}",
                        status="failed"
                    )
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error sending FCM notification to {recipient.address}: {e.response.text}")
                error_message = f"HTTP {e.response.status_code}: {e.response.text}"
                
                return NotificationResponse(
                    success=False,
                    message=f"Failed to send notification: {error_message}",
                    status="failed"
                )
            except Exception as e:
                logger.error(f"Exception sending FCM notification to {recipient.address}: {e}", exc_info=True)
                return NotificationResponse(
                    success=False,
                    message=f"Exception sending notification: {str(e)}",
                    status="failed"
                )
        
        return NotificationResponse(success=False, message="No recipients processed")
    
    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        """
        Test FCM configuration by sending a test notification.
        
        Args:
            config: FCM configuration dict
            address: Device token to send test notification to
            
        Returns:
            ProviderTestResponse with test result
        """
        try:
            fcm_config = FCMConfig.from_dict(config)
            
            # Create test FCM message
            fcm_message = {
                "message": {
                    "token": address,
                    "notification": {
                        "title": "Test Notification",
                        "body": "This is a test message from the notification service"
                    },
                    "data": {
                        "type": "test",
                        "timestamp": str(datetime.utcnow().isoformat())
                    }
                }
            }
            
            fcm_url = f"https://fcm.googleapis.com/fcm/send"
            response_data = await self.client.post(
                fcm_url,
                json={
                    "to": address,
                    "notification": {
                        "title": "Test Notification",
                        "body": "This is a test message from the notification service"
                    },
                    "data": {
                        "type": "test",
                        "timestamp": str(datetime.utcnow().isoformat())
                    }
                },
                headers={
                    "Authorization": f"key={fcm_config.server_key}",
                    "Content-Type": "application/json"
                }
            )
            
            response_data.raise_for_status()
            response_json = response_data.json()
            
            if response_json.get("success") == 1 or response_json.get("message_id"):
                return ProviderTestResponse(
                    success=True,
                    message="Test in-app notification sent successfully"
                )
            else:
                error = response_json.get("error", {})
                error_message = error.get("message", "Unknown FCM error")
                return ProviderTestResponse(
                    success=False,
                    message=f"Failed to send test notification: {error_message}"
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during FCM test: {e.response.text}")
            return ProviderTestResponse(
                success=False,
                message=f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Exception during FCM test: {e}", exc_info=True)
            return ProviderTestResponse(
                success=False,
                message=f"Exception during test: {str(e)}"
            )
    
    async def callback(self, providerCallback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process FCM delivery status callback.
        
        Args:
            providerCallback: Webhook payload from FCM
            
        Returns:
            Normalized callback data
        """
        # FCM doesn't provide webhooks in the same way as SMS providers
        # Delivery status is typically tracked via app-side acknowledgments
        # This can be implemented if needed for delivery receipts
        logger.info(f"FCM callback received: {providerCallback}")
        return {
            "status": "processed",
            "message": "FCM callback processed"
        }
    
    async def saveToOutbox(self, notificationId: str, requestObject: Dict[str, Any], retryCount: int = 0, nextRetryAt: Optional[datetime] = None) -> None:
        """
        Save failed notification to outbox for retry.
        
        Args:
            notificationId: Notification ID
            requestObject: Original request object
            retryCount: Number of retry attempts
            nextRetryAt: Next retry timestamp
        """
        # In-app notifications might not need outbox if they're fire-and-forget
        # This can be implemented if retry logic is needed
        logger.warning(f"saveToOutbox called for FCM - not implemented yet. NotificationId: {notificationId}")

