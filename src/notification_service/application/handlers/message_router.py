import logging
from typing import Dict, Optional
from notification_service.domain.interfaces.imessage_handler import IMessageHandler
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.shared.exceptions.application_exceptions import MessageRoutingError
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.entities.tenant import Tenant
from uuid import UUID
from notification_service.application.handlers.sms_channel_handler import SMSChannelHandler
from notification_service.application.handlers.in_app_channel_handler import InAppChannelHandler
from notification_service.application.handlers.email_channel_handler import EmailChannelHandler

logger = logging.getLogger(__name__)


class MessageRouter(IMessageHandler):
    """Concrete implementation of IMessageHandler for routing messages"""

    def __init__(
        self,
        smsHandler: SMSChannelHandler,
        inAppHandler: InAppChannelHandler = None,
        emailHandler: EmailChannelHandler = None,
        # whatsapp_handler: IChannelHandler
    ):
        self._handlers: Dict[NotificationChannel, IChannelHandler] = {
            NotificationChannel.SMS: smsHandler,
            NotificationChannel.INAPP: inAppHandler,
            NotificationChannel.EMAIL: emailHandler,
            # NotificationChannel.WHATSAPP: whatsappHandler,
        }

    async def doRoute(
        self, 
        channel: NotificationChannel, 
        tenant: str, 
        message: NotificationRequest,
        isImmediateMode: bool = False
    ) -> NotificationResponse:
        """
        Route message to appropriate channel handler.
        
        Args:
            channel: Notification channel (SMS, EMAIL, INAPP)
            tenant: Tenant prefix
            message: Notification request
            isImmediateMode: If True, caller expects immediate response and handles retry.
                           If False, failed messages go to outbox for automatic retry.
        """
        logger.info(f'Routing message to {channel.value} channel in {"immediate" if isImmediateMode else "fire-and-forget"} mode')
        
        handler = self._handlers.get(channel)
        if not handler:
            raise MessageRoutingError(channel.value, f'No handler configured for channel: {channel.value}')
        
        try:
           return await handler.receiveMessage(tenant, message, isImmediateMode=isImmediateMode)
        except Exception as e:
            logger.error(f'Failed to route to {channel.value}: {str(e)}', exc_info=True)
            raise MessageRoutingError(channel.value, f'Routing failed: {str(e)}') from e