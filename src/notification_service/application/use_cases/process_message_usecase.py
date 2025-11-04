import logging 


logger = logging.getLogger(__name__)
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
import re
from notification_service.domain.entities.tenant import Tenant
from notification_service.domain.value_objects.notification_response import NotificationResponse

class ProcessMessageUseCase:
    """Use case for processing incoming messages"""

    def __init__(self, message_router:IMessageHandler):
        self.message_router = message_router

    async def execute(self, channel, tenant:Tenant, message:NotificationRequest) -> NotificationResponse:
        """Process the incoming message"""
        logger.info(f"Processing message: {message}")
        # Parse the message into a NotificationRequest object
        try:
            notification_request = NotificationRequest.from_dict(message)
            message = notification_request
        except Exception as e:
            logger.error(f"Failed to parse message into NotificationRequest: {e}")
            return
        validated = self.validate_message(message, channel)
        if not validated:
            logger.warning(f"Message validation failed for channel {channel}. Skipping processing.")
            return
        return  await self.message_router.do_route(channel, tenant, message)
    
    
    def validate_message(self, message:NotificationRequest, channel:str) -> dict:
        """Validate the incoming message format"""
        # Implement validation logic here
        logger.info(f"Validating message: {message}")
        
        if not message.service_name:
            
            return {"success": False, "error": "serviceName is required"}
        if not message.recipients:
            
            return {"success": False, "error": "At least one recipient is required"}
        if not message.template_name:
            return {"success": False, "error": "templateName is required"} 
        if not message.payload:
            return {"success": False, "error": "payload is required"}
        if not message.idempotency_key:
            return {"success": False, "error": "idempotencyKey is required"}
        
        if message.recipients:
            for recipient in message.recipients:
                if not isinstance(recipient.address, str) or not recipient.address:
                    return {"success": False, "error": "Each recipient must have a valid address"}
            
            # Validate address based on channel type
                match channel.lower():
                    case "sms":
                        if not self._is_valid_phone_number(recipient.address):
                            raise ValueError(f"Invalid phone number: {recipient.address}")
                    case "email":
                        if not self._is_valid_email(recipient.address):
                            return {"success": False, "error": f"Invalid email address: {recipient.address}"}
                    case _:
                        # Default case for unknown channels
                        pass
                # Add more channel validations as needed
        
        return {"success": True, "message": "Validation passed"}
    def _is_valid_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        # Basic phone number validation (adjust regex as needed)
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(phone_pattern, phone.strip()))
        
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))