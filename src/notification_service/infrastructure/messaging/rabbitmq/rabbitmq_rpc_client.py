"""RabbitMQ RPC client implementation using aio-pika.

This client implements the RPC (Request-Reply) pattern for synchronous communication
with other microservices via RabbitMQ.

Pattern:
1. Client creates a temporary callback queue (exclusive, auto-delete)
2. Client sends request to service's RPC queue with reply_to=callback_queue
3. Client waits for response on callback queue with correlation_id matching
4. Service processes request and sends response to reply_to queue
"""
import json
import logging
import uuid
from typing import Dict, Any, Optional
import asyncio

import aio_pika
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage, AbstractQueue

from notification_service.config.settings import Settings

logger = logging.getLogger(__name__)


class RabbitMQRPCClient:
    """RabbitMQ RPC client for making synchronous request-reply calls to other services."""
    
    def __init__(self, settings: Settings):
        """Initialize RabbitMQ RPC client.
        
        Args:
            settings: Application settings containing RabbitMQ URL
        """
        self.rabbitmq_url = settings.rabbitmq_url
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[AbstractChannel] = None
        self._callback_queue: Optional[AbstractQueue] = None
        self._futures: Dict[str, asyncio.Future] = {}
        self._consumer_tag: Optional[str] = None
        
    async def connect(self) -> None:
        """Establish connection to RabbitMQ and set up callback queue."""
        try:
            # Create robust connection (auto-reconnect)
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self._channel = await self._connection.channel()
            
            # Create exclusive callback queue for receiving RPC responses
            # exclusive=True means only this connection can access it
            # auto_delete=True means it's deleted when connection closes
            self._callback_queue = await self._channel.declare_queue(
                name="",  # Let RabbitMQ generate unique name
                exclusive=True,
                auto_delete=True
            )
            
            # Start consuming responses from callback queue
            await self._callback_queue.consume(self._on_response, no_ack=True)
            
            logger.info(f"RabbitMQ RPC client connected. Callback queue: {self._callback_queue.name}")
            
        except Exception as e:
            logger.error(f"Failed to connect RabbitMQ RPC client: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        try:
            # Cancel all pending futures
            for future in self._futures.values():
                if not future.done():
                    future.set_exception(Exception("RPC client disconnected"))
            
            self._futures.clear()
            
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
            
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
            
            logger.info("RabbitMQ RPC client disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting RabbitMQ RPC client: {e}")
    
    async def _on_response(self, message: AbstractIncomingMessage) -> None:
        """Handle RPC response messages.
        
        Args:
            message: Incoming response message from RPC server
        """
        try:
            # Get correlation ID to match request with response
            correlation_id = message.correlation_id
            
            if correlation_id is None:
                logger.warning("Received response without correlation_id")
                return
            
            # Find the future waiting for this response
            future = self._futures.pop(correlation_id, None)
            
            if future is None:
                logger.warning(f"Received response for unknown correlation_id: {correlation_id}")
                return
            
            # Parse response body
            try:
                response_data = json.loads(message.body.decode())
                future.set_result(response_data)
                logger.debug(f"RPC response received for correlation_id: {correlation_id}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in RPC response: {e}")
                future.set_exception(ValueError(f"Invalid JSON response: {e}"))
                
        except Exception as e:
            logger.error(f"Error processing RPC response: {e}")
            if correlation_id and correlation_id in self._futures:
                self._futures[correlation_id].set_exception(e)
    
    async def call(
        self,
        queue_name: str,
        request_data: Dict[str, Any],
        procedure: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Make an RPC call to a service.
        
        Args:
            queue_name: Name of the RPC queue (e.g., "customer.rpc")
            request_data: Request payload as dictionary
            procedure: Optional procedure name to include in headers (for compatibility with old RPC pattern)
            timeout: Timeout in seconds (default: 30)
            
        Returns:
            Response data as dictionary
            
        Raises:
            asyncio.TimeoutError: If request times out
            RuntimeError: If client is not connected
            Exception: If RPC call fails
        """
        if not self._channel or not self._callback_queue:
            raise RuntimeError("RPC client not connected. Call connect() first.")
        
        # Generate unique correlation ID for this request
        correlation_id = str(uuid.uuid4())
        
        # Create future to wait for response
        future: asyncio.Future = asyncio.Future()
        self._futures[correlation_id] = future
        
        try:
            # Serialize request data
            request_body = json.dumps(request_data).encode()
            
            # Build headers (include procedure if provided, for compatibility with old RPC pattern)
            headers = {}
            if procedure:
                headers["procedure"] = procedure
            
            # Create RPC request message
            message = Message(
                body=request_body,
                correlation_id=correlation_id,
                reply_to=self._callback_queue.name,  # Tell server where to send response
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                headers=headers if headers else None
            )
            
            # Publish request to RPC queue
            await self._channel.default_exchange.publish(
                message,
                routing_key=queue_name
            )
            
            logger.info(f"RPC request sent to '{queue_name}' with procedure '{procedure}' and correlation_id: {correlation_id}")
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            
            logger.info(f"RPC response received from '{queue_name}' for correlation_id: {correlation_id}")
            return response
            
        except asyncio.TimeoutError:
            # Clean up future on timeout
            self._futures.pop(correlation_id, None)
            logger.error(f"RPC call to '{queue_name}' timed out after {timeout}s")
            raise
            
        except Exception as e:
            # Clean up future on error
            self._futures.pop(correlation_id, None)
            logger.error(f"RPC call to '{queue_name}' failed: {e}")
            raise
    
    @property
    def is_connected(self) -> bool:
        """Check if RPC client is connected."""
        return (
            self._connection is not None 
            and not self._connection.is_closed
            and self._channel is not None 
            and not self._channel.is_closed
        )
