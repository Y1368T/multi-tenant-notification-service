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
        smsHandler: IChannelHandler,
        inAppHandler: IChannelHandler = None,
        # email_handler: IChannelHandler,
        # whatsapp_handler: IChannelHandler
    ):
        self._handlers: Dict[NotificationChannel, IChannelHandler] = {
            NotificationChannel.SMS: smsHandler,
            NotificationChannel.PUSH: inAppHandler,
            # NotificationChannel.EMAIL: emailHandler,
            # NotificationChannel.WHATSAPP: whatsappHandler,
        }
        logger.info('MessageRouter initialized with channel handlers')

    async def doRoute(self,  channel: NotificationChannel, tenant:str, message: NotificationRequest) -> NotificationResponse:
        """Route message to appropriate channel handler."""
        logger.info(f'Routing message to {channel.value} channel')
        
        handler = self._handlers.get(channel)
        if not handler:
            raise MessageRoutingError(f'No handler configured for channel: {channel.value}')
        
        try:
           return await handler.receiveMessage(tenant, message)
        except Exception as e:
            logger.error(f'Failed to route to {channel.value}: {str(e)}', exc_info=True)
            raise MessageRoutingError(f'Routing failed for {channel.value}: {str(e)}',"exception") from e