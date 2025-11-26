import uuid
import logging
import httpx
import json
import firebase_admin
from firebase_admin import credentials, messaging
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
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

class FCMResponse(BaseModel):
    """FCM API response model"""
    success: Optional[bool] = None
    message_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

class FCMConfig(BaseModel):
    """FCM configuration model matching Firebase service account JSON"""
    type: str = "service_account"
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url: str
    universe_domain: str = "googleapis.com"
    
    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> 'FCMConfig':
        """Create FCMConfig from dictionary, supporting Firebase service account format."""
        # Check if it's already in service account format
        if "type" in data and data.get("type") == "service_account":
            return cls(
                type=data.get("type", "service_account"),
                project_id=data.get("project_id", ""),
                private_key_id=data.get("private_key_id", ""),
                private_key=data.get("private_key", ""),
                client_email=data.get("client_email", ""),
                client_id=data.get("client_id", ""),
                auth_uri=data.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                auth_provider_x509_cert_url=data.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                client_x509_cert_url=data.get("client_x509_cert_url", ""),
                universe_domain=data.get("universe_domain", "googleapis.com")
            )
        # Check if it's web app config format (apiKey, authDomain, etc.) - not supported
        if "apiKey" in data or "authDomain" in data:
            raise ValueError(
                "FCM config must be in Firebase service account format (not web app config). "
                "Please use the service account JSON file from Firebase Console > Project Settings > Service Accounts. "
                "The web app config (apiKey, authDomain, etc.) is for client-side SDK only and cannot be used with Firebase Admin SDK."
            )
        # Generic error for other formats
        raise ValueError(
            "FCM config must be in Firebase service account format with fields: "
            "type, project_id, private_key_id, private_key, client_email, client_id, etc. "
            "Please download the service account JSON from Firebase Console."
        )
    
    def toDict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with Firebase Admin SDK."""
        return {
            "type": self.type,
            "project_id": self.project_id,
            "private_key_id": self.private_key_id,
            "private_key": self.private_key,
            "client_email": self.client_email,
            "client_id": self.client_id,
            "auth_uri": self.auth_uri,
            "token_uri": self.token_uri,
            "auth_provider_x509_cert_url": self.auth_provider_x509_cert_url,
            "client_x509_cert_url": self.client_x509_cert_url,
            "universe_domain": self.universe_domain
        }
    
    def getCredentials(self) -> credentials.Certificate:
        """Get Firebase credentials object."""
        return credentials.Certificate(self.toDict())

class FCMProvider(IProviderService):
    """Firebase Cloud Messaging (FCM) provider for in-app/push notifications"""
    
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
        self.client = httpx.AsyncClient(timeout=30.0)
        self._firebase_app = None
    
    def _get_firebase_app(self, config: FCMConfig):
        """Get or initialize Firebase app with credentials."""
        try:
            # Try to get existing app
            app = firebase_admin.get_app()
            return app
        except ValueError:
            # App doesn't exist, initialize it
            cred = config.getCredentials()
            app = firebase_admin.initialize_app(cred)
            return app
    
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
        
        logger.info(f"FCM config: {tenantConfig.config}")
        fcm_config = FCMConfig.fromDict(tenantConfig.config)
        app = self._get_firebase_app(fcm_config)
        
        # Prepare FCM message for each recipient
        for recipient in requestObject.recipients:
            try:
                # Build Android config if provided
                android_config = None
                if messageToSend.get("android"):
                    android_dict = messageToSend["android"].copy()
                    # Build AndroidNotification if notification section exists
                    android_notification = None
                    if "notification" in android_dict:
                        notif_dict = android_dict.pop("notification")
                        android_notification = messaging.AndroidNotification(**notif_dict) if notif_dict else None
                    
                    # Build AndroidConfig with remaining fields
                    android_config = messaging.AndroidConfig(
                        notification=android_notification,
                        **android_dict
                    ) if android_dict else None
                
                # Build APNS config if provided
                apns_config = None
                if messageToSend.get("apns"):
                    apns_dict = messageToSend["apns"].copy()
                    headers = apns_dict.pop("headers", {})
                    payload_dict = apns_dict.pop("payload", {})
                    
                    # Build APS if provided in payload
                    aps = None
                    if "aps" in payload_dict:
                        aps_dict = payload_dict.pop("aps")
                        aps = messaging.Aps(**aps_dict) if aps_dict else None
                    
                    # Build APNSPayload
                    apns_payload = None
                    if aps:
                        # If there are other payload fields, include them
                        if payload_dict:
                            apns_payload = messaging.APNSPayload(aps=aps, **payload_dict)
                        else:
                            apns_payload = messaging.APNSPayload(aps=aps)
                    elif payload_dict:
                        # Only other payload fields, no aps
                        apns_payload = messaging.APNSPayload(**payload_dict)
                    
                    # Build APNSConfig
                    apns_config = messaging.APNSConfig(
                        headers=headers if headers else {},
                        payload=apns_payload
                    )
                
                # Convert data to FCM-compatible format (all values must be strings)
                # FCM data field requires Dict[str, str] - all values must be strings
                fcm_data = {}
                if messageToSend.get("data"):
                    data_dict = messageToSend["data"]
                    for key, value in data_dict.items():
                        # Convert all values to strings
                        if value is None:
                            fcm_data[str(key)] = ""
                        elif isinstance(value, (dict, list)):
                            # For nested structures, convert to JSON string
                            fcm_data[str(key)] = json.dumps(value)
                        else:
                            # Convert to string
                            fcm_data[str(key)] = str(value)
                
                # Build FCM message using Firebase Admin SDK
                fcm_message = messaging.Message(
                    notification=messaging.Notification(
                        title=messageToSend.get("title", "Notification"),
                        body=messageToSend.get("body", "")
                    ),
                    data=fcm_data,
                    token=recipient.address,  # Device token
                    android=android_config,
                    apns=apns_config
                )
                
                # Send message using Firebase Admin SDK
                response = messaging.send(fcm_message)
                logger.info(f"FCM message sent successfully. Message ID: {response}")
                
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
                
            except messaging.FirebaseError as e:
                error_message = f"Firebase error: {str(e)}"
                logger.error(f"Failed to send FCM notification to {recipient.address}: {error_message}")
                
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
            config: FCM configuration dict (Firebase service account format)
            address: Device token to send test notification to
            
        Returns:
            ProviderTestResponse with test result
        """
        try:
            fcm_config = FCMConfig.from_dict(config)
            
            # Initialize Firebase app with credentials
            cred = fcm_config.get_credentials()
            app = firebase_admin.initialize_app(cred)
            
            # Create test message
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Test Notification",
                    body="This is a test message from the notification service"
                ),
                token=address
            )
            
            # Send test message
            response = messaging.send(message)
            logger.info(f"FCM test response: {response}")
            
            return ProviderTestResponse(
                success=True,
                message=f"Test in-app notification sent successfully. Message ID: {response}"
            )
                
        except ValueError as e:
            logger.error(f"Configuration error during FCM test: {str(e)}")
            return ProviderTestResponse(
                success=False,
                message=f"Configuration error: {str(e)}"
            )
        except messaging.FirebaseError as e:
            logger.error(f"Firebase error during FCM test: {str(e)}")
            return ProviderTestResponse(
                success=False,
                message=f"Firebase error: {str(e)}"
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

