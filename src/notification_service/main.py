from contextlib import asynccontextmanager
import logging
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
from notification_service.application.services import tenant_sms_configuration_service
from notification_service.application.services import sms_notification_service
from notification_service.domain.interfaces.imessage_handler import IMessageHandler
from notification_service.application.handlers.message_router import MessageRouter
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.application.handlers.sms_channel_handler import SMSChannelHandler
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.Infrastructure.providers.sms.ethiotelecom_shortcode import EthioTelecomShortcodeSMSProvider
from notification_service.application.services.sms_template_service import SMSTemplateService
from notification_service.Infrastructure.providers.sms.kifiya_sms_gateway import KifiyaSMSGateway
# from notification_service.application.handlers.email_channel_handler import EmailChannelHandler
from notification_service.application.services.provider_service import ProviderService
from notification_service.domain.interfaces.imessage_consumer import IMessageConsumer

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
def main()->FastAPI:
    builder=(Builder()
    .with_title("Notification Service")
    .with_description("Service for sending notifications via email and SMS")
    .with_version("1.0.0")
    .with_lifespan(lifespan))
    register_controllers(builder)
    builder.with_singleton(Settings,instance=Settings())
    builder.with_singleton(Database)
    
    builder.with_transient(IUnitOfWork,UnitOfWork)
    builder.with_transient(EthioTelecomShortcodeSMSProvider)
    builder.with_transient(KifiyaSMSGateway)
    builder.with_transient(ProcessMessageUseCase)
    builder.with_transient(IMessageHandler,MessageRouter)
    builder.with_transient(IChannelHandler,SMSChannelHandler)
    builder.with_singleton(IMessageConsumer, RabbitMQConsumer)
    builder.with_transient(tenant_service.TenantService)
    builder.with_transient(tenant_sms_configuration_service.TenantSMSConfigurationService)
    builder.with_transient(sms_notification_service.SMSNotificationService)
    builder.with_transient(SMSTemplateService)
    builder.with_transient(ProviderService)
    
    logging.basicConfig(
    level=logging.INFO,  # Set to INFO to see info logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Output to console/docker logs
    ]
)
    
    app=builder.build()
    app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                # restrict in production e.g. ["https://app.example.com"]
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["*"],
      )
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    
    db=get_service(app,Database)
    await db.connect()
    tenantservice=get_service(app,tenant_service.TenantService)
    
    # Get ProcessMessageUseCase from DI container
    process_message_usecase = get_service(app, ProcessMessageUseCase)
    rabbit_client = get_service(app, IMessageConsumer)
    tenantservice.rabbitmq_consumer = rabbit_client
   # create rabbit client and adapter
    adapter_consumer =NotificationRabbitMQConsumer(
        rabbitmq_consumer=rabbit_client,
        tenant_service=tenantservice
    )

    # connect, ensure queues for active tenants, subscribe and start consuming
    task = asyncio.create_task(adapter_consumer.start_consuming())

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