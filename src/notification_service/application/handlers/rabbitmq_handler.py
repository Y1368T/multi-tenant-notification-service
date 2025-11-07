from notification_service.application.services.tenant_service import TenantService
from notification_service.Infrastructure.messaging.rabbitmq.rabbitmq_consumer import RabbitMQConsumer
class RabbitMQHandler:
    def __init__(self, tenant_service:TenantService,rabbitmq_consumer: RabbitMQConsumer):
        self.tenant_service = tenant_service
        self.rabbitmq_consumer = rabbitmq_consumer
        
    async def ensure_queue_exist_andsubscribe(self, queue_name: str, channel: str)->None:
        await self.rabbitmq_consumer.ensure_queue_exists_and_subscribe(queue_name=queue_name,channel=channel)