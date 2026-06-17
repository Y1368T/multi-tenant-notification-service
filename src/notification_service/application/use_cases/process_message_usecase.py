import logging 


logger = logging.getLogger(__name__)
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
import re
from notification_service.domain.value_objects.notification_response import NotificationResponse

class ProcessMessageUseCase:
    """Use case for processing incoming messages"""

    def __init__(self, messageRouter:IMessageHandler):
        self.messageRouter = messageRouter

    async def execute(
        self, 
        channel, 
        tenant: str, 
        message: NotificationRequest,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """
        Process the incoming message.
        
        Args:
            channel: Notification channel (SMS, EMAIL, INAPP)
            tenant: Tenant prefix
            message: Notification request
            isImmediateMode: If True, caller expects immediate response and handles retry.
                           If False, failed messages go to outbox for automatic retry.
        """
        logger.info(f"Processing message in {'immediate' if isImmediateMode else 'fire-and-forget'} mode: {message}")
        
        validated = self.validateMessage(message, channel)
        if not validated.get("success", False):
            error_msg = validated.get("error", "Validation failed")
            logger.warning(f"Message validation failed for channel {channel}: {error_msg}")
            return NotificationResponse(
                success=False,
                errorMessage=error_msg
            )
        return await self.messageRouter.doRoute(channel, tenant, message, isImmediateMode=isImmediateMode)
    
    
    def validateMessage(self, message:NotificationRequest, channel:str) -> dict:
        """Validate the incoming message format"""
        # Implement validation logic here
        logger.info(f"Validating message: {message}")
        
        if not message.serviceName:
            return {"success": False, "error": "serviceName is required"}
        if not getattr(message, "recipient", None) or not message.recipient.address:
            return {"success": False, "error": "recipient is required"}
        if not message.templateName:
            return {"success": False, "error": "templateName is required"}
        if not message.payload:
            return {"success": False, "error": "payload is required"}
        if not message.idempotencyKey:
            return {"success": False, "error": "idempotencyKey is required"}

        recipient = message.recipient
        if not isinstance(recipient.address, str) or not recipient.address:
            return {"success": False, "error": "recipient must have a valid address"}

        match channel.lower():
            case "sms":
                if not self.isValidPhoneNumber(recipient.address):
                    return {"success": False, "error": f"Invalid phone number: {recipient.address}"}
            case "email":
                if not self.isValidEmail(recipient.address):
                    return {"success": False, "error": f"Invalid email address: {recipient.address}"}
            # Add more channel validations as needed

        return {"success": True}
    def isValidPhoneNumber(self, phone: str) -> bool:
        """Validate phone number format"""
        # Basic phone number validation (adjust regex as needed)
        phone_pattern = r'^\+?[1-9]\d{1,14}$' 
        return bool(re.match(phone_pattern, phone.strip()))
        
    def isValidEmail(self, email: str) -> bool:
        """Validate email address format"""
        emailPattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(emailPattern, email.strip()))