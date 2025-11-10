"""RabbitMQ message consumer adapter - receives and processes notification messages."""
import logging
from typing import Dict, Any
from fastapi import Depends
import json
from uuid import UUID
from aio_pika.abc import AbstractIncomingMessage

from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_consumer import RabbitMQConsumer
from notification_service.application.services.tenant_service import TenantService

logger = logging.getLogger(__name__)


class NotificationRabbitMQConsumer:
    """
    Adapter that consumes RabbitMQ messages and triggers notification processing.
    This is the ENTRY POINT for RabbitMQ-based notifications.
    """
    
    def __init__(
        self,
        rabbitmq_consumer: RabbitMQConsumer,  # infrastructure client
        tenant_service: TenantService
    ):
        self.rabbitmq_consumer = rabbitmq_consumer
        self.tenant_service = tenant_service
        

    async def start_consuming(self) -> None:
        """Start consuming messages from all notification queues."""
        
        # Connect to RabbitMQ
        await self.rabbitmq_consumer.connect()
        logger.info("Started consuming notification messages from RabbitMQ")
        
        active_tenants = await self.tenant_service.get_tenants_for_rabbitmq()
        
        for tenant in active_tenants:
            for channel in tenant.supported_channels:
                queue_name = f"notification.{channel}.{tenant.prefix}"
                
                try:
                    # Declare queue (creates if doesn't exist, idempotent operation)
                    await self.rabbitmq_consumer.ensure_queue_exists_and_subscribe(queue_name, channel)
                    
                except Exception as e:
                    logger.error(f"Failed to setup queue {queue_name}: {e}")
    
    
    
        
                  
    
    async def stop_consuming(self) -> None:
        """Stop consuming and disconnect."""
        await self.rabbitmq_consumer.disconnect()
        logger.info("Stopped consuming notification messages")