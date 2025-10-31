"""RabbitMQ message consumer adapter - receives and processes notification messages."""
import logging
from typing import Dict, Any
import json
from uuid import UUID
from aio_pika.abc import AbstractIncomingMessage

from notification_service.Infrastructure.messaging.rabbitmq.rabbitmq_consumer import RabbitMQConsumer
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.domain.entities.tenant import Tenant

logger = logging.getLogger(__name__)


class NotificationRabbitMQConsumer:
    """
    Adapter that consumes RabbitMQ messages and triggers notification processing.
    This is the ENTRY POINT for RabbitMQ-based notifications.
    """
    
    def __init__(
        self,
        rabbitmq_consumer: RabbitMQConsumer,  # Infrastructure client
        process_message_usecase: ProcessMessageUseCase  # Application use case
    ):
        self.rabbitmq_consumer = rabbitmq_consumer
        self.process_message_usecase = process_message_usecase

    async def start_consuming(self, active_tenants: list[Tenant]) -> None:
        """Start consuming messages from all notification queues."""
        
        
                
        # Connect to RabbitMQ
        await self.rabbitmq_consumer.connect()
        
        
       
        
        logger.info("Started consuming notification messages from RabbitMQ")
        
        # Keep consuming
        await self.rabbitmq_consumer.consume()
    
    async def queue_exists(self, queue_name: str) -> bool:
        """Check if a queue exists in RabbitMQ."""
        try:
                    exists = False
                    # Preferred explicit API
                    if hasattr(self.rabbitmq_consumer, "queue_exists"):
                        exists = await self.rabbitmq_consumer.queue_exists(queue_name)
                    else:
                        # Try a passive declare if the adapter forwards that arg to the broker
                        try:
                            await self.rabbitmq_consumer.declare_queue(queue_name, passive=True)
                            exists = True
                        except TypeError:
                            # declare_queue doesn't accept passive; try a "get" style API
                            if hasattr(self.rabbitmq_consumer, "get_queue"):
                                q = await self.rabbitmq_consumer.get_queue(queue_name)
                                exists = q is not None
                            else:
                                exists = False
                        except Exception:
                            # passive declare raised because queue does not exist
                            exists = False

                    if exists:
                        logger.info(f"Queue already exists: {queue_name}")
                    else:
                        logger.info(f"Queue does not exist and will be declared: {queue_name}")

        except Exception as e:
                    logger.warning(f"Failed to check queue existence for {queue_name}: {e}")  
                    
                        
    async def _handle_email_message(self, message: AbstractIncomingMessage) -> None:
        """Handle incoming email notification message."""
        async with message.process():
            try:
                # Parse message body
                payload = json.loads(message.body.decode())
                queue_name = message.method.routing_key
                
                queue_parts = queue_name.split('.')
                if len(queue_parts) != 3 or queue_parts[0] != "notification":
                    raise ValueError(f"Invalid queue name format: {queue_name}")
                tenant_prefix = queue_parts[2]
                
                
                # Convert to domain value object
                notification_request = NotificationRequest.from_dict(payload)
                
                # Call use case to process notification
                await self.process_message_usecase.execute(NotificationChannel.EMAIL, tenant=tenant_prefix, notification_request=notification_request)
                
                logger.info(f"Successfully processed email notification")
                
            except Exception as e:
                logger.error(f"Error processing email message: {e}")
                raise  # Will be requeued
    
    async def _handle_sms_message(self, message: AbstractIncomingMessage) -> None:
        """Handle incoming SMS notification message."""
        async with message.process():
            try:
                payload = json.loads(message.body.decode())
                
                logger.info(f"Received SMS notification: {payload}")
                
                notification_request = NotificationRequest.from_dict(payload)
                queue_name = message.method.routing_key
                
                queue_parts = queue_name.split('.')
                if len(queue_parts) != 3 or queue_parts[0] != "notification":
                    raise ValueError(f"Invalid queue name format: {queue_name}")
                tenant_prefix = queue_parts[2]


                await self.process_message_usecase.execute(NotificationChannel.SMS, tenant=tenant_prefix, notification_request=notification_request)

                logger.info(f"Successfully processed SMS notification")
                
            except Exception as e:
                logger.error(f"Error processing SMS message: {e}")
                raise
    
    async def _handle_in_app_message(self, message: AbstractIncomingMessage) -> None:
        """Handle incoming in-app notification message."""
        async with message.process():
            try:
                payload = json.loads(message.body.decode())
                
                logger.info(f"Received in-app notification: {payload}")
                
                notification_request = NotificationRequest.from_dict(payload)
                queue_name = message.method.routing_key
                
                queue_parts = queue_name.split('.')
                if len(queue_parts) != 3 or queue_parts[0] != "notification":
                    raise ValueError(f"Invalid queue name format: {queue_name}")
                tenant_prefix = queue_parts[2]

                await self.process_message_usecase.execute(NotificationChannel.IN_APP, tenant=tenant_prefix, notification_request=notification_request)

                logger.info(f"Successfully processed in-app notification")
                
            except Exception as e:
                logger.error(f"Error processing in-app message: {e}")
                raise
    
    async def stop_consuming(self) -> None:
        """Stop consuming and disconnect."""
        await self.rabbitmq_consumer.disconnect()
        logger.info("Stopped consuming notification messages")