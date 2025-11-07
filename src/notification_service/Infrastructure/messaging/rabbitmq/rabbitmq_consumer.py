"""RabbitMQ consumer implementation using aio-pika."""
import json
import logging
from typing import Callable, Awaitable, Dict, Any, Optional
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.abc import AbstractRobustConnection, AbstractChannel, AbstractQueue, AbstractIncomingMessage
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.config.settings import Settings



from notification_service.domain.interfaces import IMessageConsumer

logger = logging.getLogger(__name__)


class RabbitMQConsumer(IMessageConsumer):
    """RabbitMQ consumer implementation with async support."""
    
    def __init__(self,settings:Settings,process_message_usecase:ProcessMessageUseCase):
        """Initialize RabbitMQ consumer.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL (e.g., amqp://guest:guest@localhost/)
        """
        self.rabbitmq_url = settings.rabbitmq_url
        self.process_message_usecase = process_message_usecase
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[AbstractChannel] = None
        self._subscriptions: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self._queues: Dict[str, AbstractQueue] = {}  # Cache for declared queues
    
    async def connect(self) -> None:
        """Establish connection to RabbitMQ broker."""
        try:
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self._channel = await self._connection.channel()
            
            # Set QoS - process one message at a time
            await self._channel.set_qos(prefetch_count=1)
            
            logger.info("RabbitMQ consumer connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        try:
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
            
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
            
            logger.info("RabbitMQ consumer disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._connection is not None and self._channel is not None
    
        
    async def subscribe(
        self,
        queue_name: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Subscribe to a queue and process messages with callback.
        
        Args:
            queue_name: Queue name (e.g., "notification.email")
            callback: Async function to process each message
        """
        if not self._channel:
            raise RuntimeError("RabbitMQ channel not initialized. Call connect() first.")
        
        try:
            # Declare queue (idempotent - will create if doesn't exist)
            queue = await self._channel.declare_queue(
                queue_name,
                durable=True,  # Survive broker restarts
                auto_delete=False
            )
            
            # Store callback for this queue
            self._subscriptions[queue_name] = callback
            
            # Create message handler wrapper
            async def message_handler(message: AbstractIncomingMessage) -> None:
                async with message.process():
                    try:
                        # Decode message body
                        body = message.body.decode()
                        payload = json.loads(body)
                        
                        logger.info(f"Received message from queue '{queue_name}': {payload}")
                        
                        # Process message with callback
                        await callback(message)
                        
                        logger.info(f"Successfully processed message from queue '{queue_name}'")
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message from '{queue_name}': {e}")
                        # Message will be rejected (not requeued)
                    except Exception as e:
                        logger.error(f"Error processing message from '{queue_name}': {e}")
                        # Message will be rejected and requeued for retry
                        raise
            
            # Start consuming messages
            await queue.consume(message_handler)
            
            logger.info(f"Subscribed to queue '{queue_name}'")
        except Exception as e:
            logger.error(f"Error subscribing to queue '{queue_name}': {e}")
            raise
    
    async def consume(self) -> None:
        """Start consuming messages from subscribed queues.
        
        This method keeps the consumer running indefinitely.
        """
        if not self._subscriptions:
            logger.warning("No subscriptions found. Call subscribe() before consume().")
            return
        
        logger.info(f"Consuming from {len(self._subscriptions)} queue(s)")
        
        try:
            # Keep the consumer running
            # The actual message consumption happens in the callbacks set up in subscribe()
            # This method just keeps the connection alive
            await self._connection.ready()
        except Exception as e:
            logger.error(f"Error during message consumption: {e}")
            raise
    
    
    async def declare_queue(
        self, 
        queue_name: str, 
        durable: bool = True, 
        auto_delete: bool = False,
        **kwargs
    ) -> AbstractQueue:
        """
        Declare a queue (creates if doesn't exist, idempotent).
        
        Args:
            queue_name: Name of the queue
            durable: Queue survives broker restart
            auto_delete: Delete queue when no consumers
            **kwargs: Additional queue arguments
            
        Returns:
            The declared queue
        """
        if not self._channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")
        
        try:
            queue = await self._channel.declare_queue(
                queue_name,
                durable=durable,
                auto_delete=auto_delete,
                **kwargs
            )
            
            self._queues[queue_name] = queue
            logger.info(f"Queue declared: {queue_name} (durable={durable})")
            return queue
            
        except Exception as e:
            logger.error(f"Failed to declare queue {queue_name}: {e}")
            raise
       
    async def ensure_queue_exists_and_subscribe(self, queue_name: str, channel: str) -> None:
        """
        Ensure queue exists (create if needed) and subscribe to it.
        
        Args:
            queue_name: Name of the queue (e.g., "notification.sms.trucksload")
            channel: Notification channel type (sms, email, in_app)
        """
        try:
            # Step 1: Declare queue (idempotent - creates if doesn't exist, returns existing if exists)
            queue = await self.declare_queue(
                queue_name=queue_name,
                durable=True,  # Survive broker restarts
                auto_delete=False  # Don't delete when no consumers
            )
            
            logger.info(f"Queue ensured: {queue_name}")
            
            # Step 2: Subscribe to the queue based on channel type
            handler = self._get_handler_for_channel(channel)
            
            await self.subscribe(queue_name, handler)
            
            logger.info(f"Subscribed to queue: {queue_name} with {handler.__name__}")
            
        except Exception as e:
            logger.error(f"Error ensuring queue {queue_name}: {e}")
            raise
    
    def _get_handler_for_channel(self, channel: str):
        """Get the appropriate message handler for the channel type."""
        handlers = {
            "sms": self._handle_sms_message,
            "email": self._handle_email_message,
            "in_app": self._handle_in_app_message,
        }
        
        handler = handlers.get(channel.lower())
        if not handler:
            raise ValueError(f"No handler found for channel: {channel}")
        
        return handler
    
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
                queue_name = message.routing_key
                
                queue_parts = queue_name.split('.')
                if len(queue_parts) != 3 or queue_parts[0] != "notification":
                    raise ValueError(f"Invalid queue name format: {queue_name}")
                tenant_prefix = queue_parts[2]


                await self.process_message_usecase.execute(NotificationChannel.SMS, tenant_prefix, notification_request)

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
    