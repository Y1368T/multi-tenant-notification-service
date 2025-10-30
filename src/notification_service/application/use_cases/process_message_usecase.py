import logging 


logger = logging.getLogger(__name__)
from notification_service.domain.interfaces import IMessageHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
import re

class ProcessMessageUseCase:
    """Use case for processing incoming messages"""

    def __init__(self, message_router:IMessageHandler):
        self.message_router = message_router

    async def execute(self, channel, tenant, message):
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
        await self.message_router.do_route(channel, tenant, message)
    
    
    def validate_message(self, message:NotificationRequest, channel:str) -> bool:
        """Validate the incoming message format"""
        # Implement validation logic here
        logger.info(f"Validating message: {message}")
        
        if not message.service_name:
            logger.error("serviceName is required")
            return False
        if not message.recipients:
            logger.error("recipients list cannot be empty") 
            return False
        if not message.template_name:
            logger.error("templateName is required")
            return False
        if not message.payload:
            logger.error("payload is required") 
            return False
        if not message.idempotency_key:
            logger.error("idempotencyKey is required")
            return False
        
        if message.recipients:
            for recipient in message.recipients:
                if not isinstance(recipient.address, str) or not recipient.address:
                    raise ValueError("Each recipient must have a valid address")
            
            # Validate address based on channel type
            match channel.lower():
                case "sms":
                    if not self._is_valid_phone_number(recipient.address):
                        raise ValueError(f"Invalid phone number: {recipient.address}")
                case "email":
                    if not self._is_valid_email(recipient.address):
                        raise ValueError(f"Invalid email address: {recipient.address}")
                case _:
                    # Default case for unknown channels
                    pass
            # Add more channel validations as needed
        
    def _is_valid_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        # Basic phone number validation (adjust regex as needed)
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(phone_pattern, phone.strip()))
        
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))