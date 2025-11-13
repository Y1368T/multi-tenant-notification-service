from notification_service.application.services.tenant_service import TenantService
from notification_service.infrastructure.messaging.rabbitmq.rabbitmq_consumer import RabbitMQConsumer
class RabbitMQHandler:
    def __init__(self, tenantService:TenantService,rabbitmqConsumer: RabbitMQConsumer):
        self.tenantService = tenantService
        self.rabbitmqConsumer = rabbitmqConsumer
        
    async def ensureQueueExistAndSubscribe(self, queueName: str, channel: str)->None:
        await self.rabbitmqConsumer.ensureQueueExistsAndSubscribe(queueName=queueName,channel=channel)