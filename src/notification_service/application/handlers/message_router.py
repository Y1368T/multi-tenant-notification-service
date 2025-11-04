import logging
from typing import Dict 
from notification_service.domain.interfaces.imessage_handler import IMessageHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.shared.exceptions.application_exceptions import MessageRoutingError
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant import Tenant
from uuid import UUID
logger = logging.getLogger(__name__)

class MessageRouter(IMessageHandler):
    """Concrete implementation of IMessageHandler for routing messages"""

    def __init__(
        self,
        sms_handler: IChannelHandler,
        # email_handler: IChannelHandler,
        # push_handler: IChannelHandler,
        # whatsapp_handler: IChannelHandler
    ):
        self._handlers: Dict[NotificationChannel, IChannelHandler] = {
            NotificationChannel.SMS: sms_handler
            # NotificationChannel.EMAIL: email_handler,
            # NotificationChannel.PUSH: push_handler,
            # NotificationChannel.WHATSAPP: whatsapp_handler
        }
        logger.info('MessageRouter initialized with 4 channel handlers')

    async def do_route(self,  channel: NotificationChannel, tenant:Tenant, message: NotificationRequest) -> NotificationResponse:
        """Route message to appropriate channel handler."""
        logger.info(f'Routing message to {channel.value} channel')
        
        handler = self._handlers.get(channel)
        if not handler:
            raise MessageRoutingError(f'No handler configured for channel: {channel.value}')
        
        try:
           return await handler.receive_message(tenant, message)
        except Exception as e:
            logger.error(f'Failed to route to {channel.value}: {str(e)}', exc_info=True)
            raise MessageRoutingError(f'Routing failed for {channel.value}: {str(e)}',"exception") from e