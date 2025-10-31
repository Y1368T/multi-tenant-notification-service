from contextlib import asynccontextmanager
from qena_shared_lib.application import Builder
from notification_service.Infrastructure.persisitence.db_session.session import Database
from notification_service.Infrastructure.messaging.rabbitmq import RabbitMQConsumer
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.application.services import tenant_service
from notification_service.adpaters.inbound.rabbitmq.rabbitmq_consumer import NotificationRabbitMQConsumer
from notification_service.Infrastructure.persisitence.unit_of_work import UnitOfWork
from  notification_service.config.settings import settings
from notification_service.Infrastructure.persisitence.mappers.tenant_mapper import TenantMapper
from notification_service.Infrastructure.persisitence.repositories.tenant_repository import TenantRepository
import asyncio
import types
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adpaters.inbound.rest.routers import register_controllers
from notification_service.config.settings import Settings
from qena_shared_lib.dependencies.http import get_service

from fastapi import FastAPI

def main()->FastAPI:
    builder=(Builder()
    .with_title("Notification Service")
    .with_description("Service for sending notifications via email and SMS")
    .with_version("1.0.0")
    .with_lifespan(lifespan))
    register_controllers(builder)
    builder.with_singleton(Settings,instance=Settings())
    builder.with_singleton(Database)
    
    builder.with_singleton(IUnitOfWork,UnitOfWork)
    
    builder.with_singleton(tenant_service.TenantService)
    
    app=builder.build()
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    
    db=get_service(app,Database)
    await db.connect()
    uow=get_service(app,IUnitOfWork)
    uow.set_constructor()
    tenantservice=get_service(app,tenant_service.TenantService)
    active_tenants = await tenantservice.get_active_tenants()
    queu_name="notification.sms.qena"
    # create rabbit client and adapter (process use case can be injected later)
    rabbit_client = RabbitMQConsumer(settings.rabbitmq_url)
    adapter_consumer = NotificationRabbitMQConsumer(
        rabbitmq_consumer=rabbit_client,
        process_message_usecase=None
    )

    # connect, ensure queues for active tenants, subscribe and start consuming
    task = asyncio.create_task(adapter_consumer.start_consuming(active_tenants=active_tenants))

    try:
        yield
    finally:
        # Shutdown actions
        await adapter_consumer.stop_consuming()
        db.disconnect()
        
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)




    



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("notification_service.main:main",factory=True, host="0.0.0.0", port=8000)