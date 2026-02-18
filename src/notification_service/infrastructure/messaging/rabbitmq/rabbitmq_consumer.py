"""RabbitMQ consumer implementation using aio-pika."""
import json
import logging
from select import select
from typing import Callable, Awaitable, Dict, Any, Optional
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from sqlalchemy.ext.asyncio import AsyncSession
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.abc import AbstractRobustConnection, AbstractChannel, AbstractQueue, AbstractIncomingMessage
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import NotificationResponse
from notification_service.domain.value_objects.notification_types import NotificationChannel
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.config.settings import Settings



from notification_service.domain.interfaces import IMessageConsumer

logger = logging.getLogger(__name__)


class RabbitMQConsumer(IMessageConsumer):
    """RabbitMQ consumer implementation with async support."""
    
    def __init__(self,settings:Settings,
                 processMessageUseCase:ProcessMessageUseCase
                 ):
        """Initialize RabbitMQ consumer.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL (e.g., amqp://guest:guest@localhost/)
        """
        self.rabbitmq_url = settings.rabbitmq_url
        self.processMessageUseCase = processMessageUseCase
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
    def isConnected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._connection is not None and self._channel is not None
    
        
    async def subscribe(
        self,
        queueName: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Subscribe to a queue and process messages with callback.
        
        Args:
            queueName: Queue name (e.g., "notification.email")
            callback: Async function to process each message
        """
        if not self._channel:
            raise RuntimeError("RabbitMQ channel not initialized. Call connect() first.")
        
        try:
            # Declare queue (idempotent - will create if doesn't exist)
            queue = await self._channel.declare_queue(
                queueName,
                durable=True,  # Survive broker restarts
                auto_delete=False
            )
            
            # Store callback for this queue
            self._subscriptions[queueName] = callback
            
            # Create message handler wrapper
            async def messageHandler(message: AbstractIncomingMessage) -> None:
                async with message.process():
                    try:
                        # Decode message body
                        body = message.body.decode()
                        payload = json.loads(body)
                        
                        logger.info(f"Received message from queue '{queueName}': {payload}")
                        
                        # Process message with callback
                        await callback(message)
                        
                        logger.info(f"Successfully processed message from queue '{queueName}'")
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message from '{queueName}': {e}")
                        # Message will be rejected (not requeued)
                    except Exception as e:
                        logger.error(f"Error processing message from '{queueName}': {e}")
                        # Message will be rejected and requeued for retry
                        raise
            
            # Start consuming messages
            await queue.consume(messageHandler)
            
        except Exception as e:
            logger.error(f"Error subscribing to queue '{queueName}': {e}")
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
    
    
    async def declareQueue(
        self, 
        queueName: str, 
        durable: bool = True, 
        autoDelete: bool = False,
        **kwargs
    ) -> AbstractQueue:
        """
        Declare a queue (creates if doesn't exist, idempotent).
        
        Args:
            queueName: Name of the queue
            durable: Queue survives broker restart
            autoDelete: Delete queue when no consumers
            **kwargs: Additional queue arguments
            
        Returns:
            The declared queue
        """
        if not self._channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")
        
        try:
            queue = await self._channel.declare_queue(
                queueName,
                durable=durable,
                auto_delete=autoDelete,
                **kwargs
            )
            
            self._queues[queueName] = queue
            return queue
            
        except Exception as e:
            logger.error(f"Failed to declare queue {queueName}: {e}")
            raise
       
    async def ensureQueueExistsAndSubscribe(self, queueName: str, channel: str) -> None:
        """
        Ensure queue exists (create if needed) and subscribe to it.
        
        Args:
            queueName: Name of the queue (e.g., "notification.sms.trucksload")
            channel: Notification channel type (sms, email, in_app)
        """
        try:
            # Step 1: Declare queue (idempotent - creates if doesn't exist, returns existing if exists)
            queue = await self.declareQueue(
                queueName=queueName,
                durable=True,  # Survive broker restarts
                autoDelete=False  # Don't delete when no consumers
            )
            
            # Step 2: Subscribe to the queue based on channel type
            handler = self.getHandlerForChannel(channel)
            
            await self.subscribe(queueName, handler)
            
            
        except Exception as e:
            logger.error(f"Error ensuring queue {queueName}: {e}")
            raise
    
    async def unsubscribeAndDeleteQueue(self, queueName: str) -> bool:
        """
        Unsubscribe from a queue and optionally delete it.
        
        Args:
            queueName: Name of the queue to unsubscribe from and delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._channel:
                logger.warning(f"Cannot unsubscribe from {queueName}: channel not initialized")
                return False
            
            # Remove from subscriptions
            if queueName in self._subscriptions:
                del self._subscriptions[queueName]
                logger.info(f"Removed subscription for queue: {queueName}")
            
            # Cancel consumer and delete queue if it exists in cache
            if queueName in self._queues:
                queue = self._queues[queueName]
                try:
                    # Cancel all consumers on this queue
                    # Note: aio-pika handles consumer cancellation when queue is deleted
                    await queue.delete(if_unused=False, if_empty=False)
                    logger.info(f"Deleted queue: {queueName}")
                except Exception as e:
                    logger.warning(f"Could not delete queue {queueName}: {e}")
                
                del self._queues[queueName]
            else:
                # Queue not in cache, try to declare and delete
                try:
                    queue = await self._channel.declare_queue(
                        queueName,
                        durable=True,
                        passive=True  # Don't create, just check if exists
                    )
                    await queue.delete(if_unused=False, if_empty=False)
                    logger.info(f"Deleted queue: {queueName}")
                except Exception as e:
                    # Queue might not exist, that's OK
                    logger.info(f"Queue {queueName} does not exist or already deleted: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from queue {queueName}: {e}")
            return False
    
    async def unsubscribeFromTenantQueues(self, tenantPrefix: str, channels: list) -> None:
        """
        Unsubscribe and delete all queues for a tenant.
        
        Args:
            tenantPrefix: The tenant prefix (e.g., "DEMO")
            channels: List of channels to remove (e.g., ["sms", "email", "inapp"])
        """
        for channel in channels:
            queueName = f"notification.{channel}.{tenantPrefix}"
            await self.unsubscribeAndDeleteQueue(queueName)
    
    def getHandlerForChannel(self, channel: str):
        """Get the appropriate message handler for the channel type."""
        handlers = {
            "sms": self.handleSmsMessage,
            "email": self.handleEmailMessage,
            "inapp": self.handleInAppMessage,
        }
        
        handler = handlers.get(channel.lower())
        if not handler:
            raise ValueError(f"No handler found for channel: {channel}")
        
        return handler
    
    def _is_rpc_mode(self, message: AbstractIncomingMessage) -> bool:
        """
        Check if message expects RPC response (immediate mode).
        
        RPC mode is detected when message has both reply_to and correlation_id.
        """
        return bool(message.reply_to and message.correlation_id)
    
    async def _send_rpc_response(
        self, 
        original_message: AbstractIncomingMessage, 
        response: NotificationResponse
    ) -> None:
        """
        Send RPC response to caller's reply_to queue.
        
        Args:
            original_message: The incoming message with reply_to and correlation_id
            response: NotificationResponse to send back
        """
        if not original_message.reply_to or not original_message.correlation_id:
            logger.warning("Cannot send RPC response: missing reply_to or correlation_id")
            return
        
        if not self._channel:
            logger.error("Cannot send RPC response: channel not initialized")
            return
        
        try:
            # Convert response to dict for JSON serialization
            # Note: NotificationResponse doesn't have 'status' or 'notificationId' directly
            # Those are on recipientResponse items
            response_dict = {
                "success": response.success,
                "message": response.message,
                "errorMessage": response.errorMessage,
                "channel": response.channel,
                "tenantId": response.tenantId
            }
            
            # Include recipient responses if available
            if response.recipientResponse:
                if isinstance(response.recipientResponse, list):
                    response_dict["recipientResponse"] = [
                        {
                            "notificationId": r.notificationId,
                            "status": r.status,
                            "recipient": r.recipient,
                            "success": r.success,
                            "message": r.message,
                            "errorMessage": r.errorMessage
                        } for r in response.recipientResponse
                    ]
                else:
                    r = response.recipientResponse
                    response_dict["recipientResponse"] = {
                        "notificationId": r.notificationId,
                        "status": r.status,
                        "recipient": r.recipient,
                        "success": r.success,
                        "message": r.message,
                        "errorMessage": r.errorMessage
                    }
            
            response_message = Message(
                body=json.dumps(response_dict).encode(),
                correlation_id=original_message.correlation_id,
                content_type="application/json"
            )
            
            await self._channel.default_exchange.publish(
                response_message,
                routing_key=original_message.reply_to
            )
            
            logger.info(
                f"RPC response sent to {original_message.reply_to}: "
                f"correlation_id={original_message.correlation_id}, success={response.success}"
            )
            
        except Exception as e:
            logger.error(f"Failed to send RPC response: {e}", exc_info=True)
    
    async def handleEmailMessage(self, message: AbstractIncomingMessage) -> None:
        """Handle incoming email notification message."""
        response = None
        try:
            # Parse message body
            payload = json.loads(message.body.decode())
            queue_name = message.routing_key
            
            queue_parts = queue_name.split('.')
            if len(queue_parts) != 3 or queue_parts[0] != "notification":
                raise ValueError(f"Invalid queue name format: {queue_name}")
            tenant_prefix = queue_parts[2]
            
            # Detect processing mode
            is_immediate_mode = self._is_rpc_mode(message)
            logger.info(f"Processing email notification in {'immediate' if is_immediate_mode else 'fire-and-forget'} mode")
            
            # Convert to domain value object
            notification_request = NotificationRequest.fromDict(payload)
            
            # Call use case to process notification with mode flag
            response = await self.processMessageUseCase.execute(
                NotificationChannel.EMAIL, 
                tenant_prefix, 
                notification_request,
                isImmediateMode=is_immediate_mode
            )
            
            logger.info(f"Successfully processed email notification")
            
        except Exception as e:
            logger.error(f"Error processing email message: {e}")
            # Create error response for RPC mode
            response = NotificationResponse(
                success=False,
                errorMessage=str(e),
                message="Failed to process notification"
            )
            raise  # Will be requeued
        finally:
            # Send RPC response if in immediate mode
            if self._is_rpc_mode(message) and response:
                await self._send_rpc_response(message, response)
    
    async def handleSmsMessage(self, message: AbstractIncomingMessage) -> None:
        """Handle incoming SMS notification message."""
        response = None
        try:
            payload = json.loads(message.body.decode())
            
            logger.info(f"Received SMS notification: {payload}")
            
            notification_request = NotificationRequest.fromDict(payload)
            queue_name = message.routing_key
            
            queue_parts = queue_name.split('.')
            if len(queue_parts) != 3 or queue_parts[0] != "notification":
                raise ValueError(f"Invalid queue name format: {queue_name}")
            tenant_prefix = queue_parts[2]
            
            # Detect processing mode
            is_immediate_mode = self._is_rpc_mode(message)
            logger.info(f"Processing SMS notification in {'immediate' if is_immediate_mode else 'fire-and-forget'} mode")
            
            response = await self.processMessageUseCase.execute(
                NotificationChannel.SMS, 
                tenant_prefix, 
                notification_request,
                isImmediateMode=is_immediate_mode
            )

            logger.info(f"Successfully processed SMS notification")
                
        except Exception as e:
            logger.error(f"Error processing SMS message: {e}")
            response = NotificationResponse(
                success=False,
                errorMessage=str(e),
                message="Failed to process notification"
            )
            raise
        finally:
            if self._is_rpc_mode(message) and response:
                await self._send_rpc_response(message, response)
    
    async def handleInAppMessage(self, message: AbstractIncomingMessage) -> None:
        """Handle incoming in-app notification message."""
        response = None
        try:
            payload = json.loads(message.body.decode())
            
            logger.info(f"Received in-app notification: {payload}")
            
            notification_request = NotificationRequest.fromDict(payload)
            queue_name = message.routing_key
            
            queue_parts = queue_name.split('.')
            if len(queue_parts) != 3 or queue_parts[0] != "notification":
                raise ValueError(f"Invalid queue name format: {queue_name}")
            tenant_prefix = queue_parts[2]
            
            # Detect processing mode
            is_immediate_mode = self._is_rpc_mode(message)
            logger.info(f"Processing in-app notification in {'immediate' if is_immediate_mode else 'fire-and-forget'} mode")

            response = await self.processMessageUseCase.execute(
                NotificationChannel.INAPP, 
                tenant_prefix, 
                notification_request,
                isImmediateMode=is_immediate_mode
            )

            logger.info(f"Successfully processed in-app notification")
                
        except Exception as e:
            logger.error(f"Error processing in-app message: {e}")
            response = NotificationResponse(
                success=False,
                errorMessage=str(e),
                message="Failed to process notification"
            )
            raise
        finally:
            if self._is_rpc_mode(message) and response:
                await self._send_rpc_response(message, response)
    