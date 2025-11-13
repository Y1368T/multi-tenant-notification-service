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
        rabbitmqConsumer: RabbitMQConsumer,  # infrastructure client
        tenantService: TenantService
    ):
        self.rabbitmqConsumer = rabbitmqConsumer
        self.tenantService = tenantService
        

    async def startConsuming(self) -> None:
        """Start consuming messages from all notification queues."""
        
        # Connect to RabbitMQ
        await self.rabbitmqConsumer.connect()
        logger.info("Started consuming notification messages from RabbitMQ")
        
        activeTenants = await self.tenantService.getTenantsForRabbitmq()
        
        for tenant in activeTenants:
            for channel in tenant.supportedChannels:
                queueName = f"notification.{channel}.{tenant.prefix}"
                
                try:
                    # Declare queue (creates if doesn't exist, idempotent operation)
                    await self.rabbitmqConsumer.ensureQueueExistsAndSubscribe(queueName, channel)
                    
                except Exception as e:
                    logger.error(f"Failed to setup queue {queueName}: {e}")
    
    
    
        
                  
    
    async def stopConsuming(self) -> None:
        """Stop consuming and disconnect."""
        await self.rabbitmqConsumer.disconnect()
        logger.info("Stopped consuming notification messages")