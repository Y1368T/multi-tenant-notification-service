"""
Message queue interface.
Abstraction for RabbitMQ/Kafka message consumption.
"""
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Dict, Any


class IMessageConsumer(ABC):
    """Interface for message queue operations."""
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to message broker.
        Should handle connection pooling and reconnection logic.
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to message broker."""
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        queueName: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Subscribe to a queue and process messages with callback.
        
        Args:
            queueName: Queue pattern (e.g., "notification.sms.qena")
            callback: Async function to process each message
        """
        pass
    
    @abstractmethod
    async def consume(self) -> None:
        """
        Start consuming messages from subscribed queues.
        Should run indefinitely until stopped.
        """
        pass
    
    