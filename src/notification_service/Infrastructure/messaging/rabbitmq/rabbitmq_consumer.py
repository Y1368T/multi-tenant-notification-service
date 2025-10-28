from notification_service.domain.interfaces import IMessageConsumer
class RabbitMQConsumer(IMessageConsumer):
    def connect(self):
        pass
    def disconnect(self):
        pass
    def subscribe(self, queue_name: str, callback):
        pass
    def publish(self, queue_name: str, message):
        pass
    def consume(self):
        pass