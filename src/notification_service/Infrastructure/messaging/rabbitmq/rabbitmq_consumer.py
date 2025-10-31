"""RabbitMQ consumer implementation using aio-pika."""
import json
import logging
from typing import Callable, Awaitable, Dict, Any, Optional
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.abc import AbstractIncomingMessage

from notification_service.domain.interfaces import IMessageConsumer

logger = logging.getLogger(__name__)


class RabbitMQConsumer(IMessageConsumer):
    """RabbitMQ consumer implementation with async support."""
    
    def __init__(self, rabbitmq_url: str):
        """Initialize RabbitMQ consumer.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL (e.g., amqp://guest:guest@localhost/)
        """
        self.rabbitmq_url = rabbitmq_url
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._subscriptions: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
    
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
                        await callback(payload)
                        
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
    
    async def publish(
        self,
        queue_name: str,
        message: Dict[str, Any]
    ) -> None:
        """Publish a message to a queue.
        
        Args:
            queue_name: Target queue name
            message: Message payload (will be JSON serialized)
        """
        if not self._channel:
            raise RuntimeError("RabbitMQ channel not initialized. Call connect() first.")
        
        try:
            # Declare queue (idempotent)
            queue = await self._channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False
            )
            
            # Serialize message to JSON
            body = json.dumps(message, default=str)
            
            # Create message
            rabbitmq_message = Message(
                body=body.encode(),
                delivery_mode=DeliveryMode.PERSISTENT,  # Survive broker restarts
                content_type="application/json"
            )
            
            # Publish to queue
            await self._channel.default_exchange.publish(
                rabbitmq_message,
                routing_key=queue_name
            )
            
            logger.info(f"Published message to queue '{queue_name}'")
        except Exception as e:
            logger.error(f"Error publishing message to queue '{queue_name}': {e}")
            raise
    
    async def declare_exchange(
        self,
        exchange_name: str,
        exchange_type: str = "topic"
    ) -> None:
        """Declare an exchange for routing messages.
        
        Args:
            exchange_name: Name of the exchange
            exchange_type: Type of exchange (topic, direct, fanout, headers)
        """
        if not self._channel:
            raise RuntimeError("RabbitMQ channel not initialized. Call connect() first.")
        
        try:
            exchange_type_map = {
                "topic": ExchangeType.TOPIC,
                "direct": ExchangeType.DIRECT,
                "fanout": ExchangeType.FANOUT,
                "headers": ExchangeType.HEADERS
            }
            
            await self._channel.declare_exchange(
                exchange_name,
                exchange_type_map.get(exchange_type, ExchangeType.TOPIC),
                durable=True
            )
            
            logger.info(f"Declared exchange '{exchange_name}' of type '{exchange_type}'")
        except Exception as e:
            logger.error(f"Error declaring exchange '{exchange_name}': {e}")
            raise
    
    async def bind_queue_to_exchange(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str
    ) -> None:
        """Bind a queue to an exchange with a routing key.
        
        Args:
            queue_name: Name of the queue
            exchange_name: Name of the exchange
            routing_key: Routing key pattern (e.g., "notification.email.*")
        """
        if not self._channel:
            raise RuntimeError("RabbitMQ channel not initialized. Call connect() first.")
        
        try:
            # Declare queue
            queue = await self._channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False
            )
            
            # Declare exchange
            exchange = await self._channel.get_exchange(exchange_name)
            
            # Bind queue to exchange
            await queue.bind(exchange, routing_key=routing_key)
            
            logger.info(f"Bound queue '{queue_name}' to exchange '{exchange_name}' with routing key '{routing_key}'")
        except Exception as e:
            logger.error(f"Error binding queue '{queue_name}' to exchange '{exchange_name}': {e}")
            raise