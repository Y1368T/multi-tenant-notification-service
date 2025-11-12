from contextlib import asynccontextmanager
import logging
from qena_shared_lib.application import Builder
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.messaging.rabbitmq import RabbitMQConsumer
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.application.services import tenant_service
from notification_service.adapters.inbound.rabbitmq.rabbitmq_consumer import NotificationRabbitMQConsumer
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
from  notification_service.config.settings import settings
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper
from notification_service.infrastructure.persistence.repositories.tenant_repository import TenantRepository
import asyncio
import types
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.rest.routers import register_controllers
from notification_service.config.settings import Settings
from qena_shared_lib.dependencies.http import get_service
from notification_service.application.services import tenant_sms_configuration_service
from notification_service.application.services import sms_notification_service
from notification_service.domain.interfaces.imessage_handler import IMessageHandler
from notification_service.application.handlers.message_router import MessageRouter
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.application.handlers.sms_channel_handler import SMSChannelHandler
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.infrastructure.providers.sms.ethiotelecom_shortcode import EthioTelecomShortcodeSMSProvider
from notification_service.application.services.sms_template_service import SMSTemplateService
from notification_service.infrastructure.providers.sms.kifiya_sms_gateway import KifiyaSMSGateway
# from notification_service.application.handlers.email_channel_handler import EmailChannelHandler
from notification_service.application.services.provider_service import ProviderService
from notification_service.domain.interfaces.imessage_consumer import IMessageConsumer

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from typing import Any, Dict
from notification_service.shared.exceptions.application_exceptions import (
    ApplicationException,
    EntityNotFoundError,
    ValidationError,
    ConflictError
)

def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Custom OpenAPI schema generator that fixes anyOf null type issues."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Fix OpenAPI version format
    openapi_schema["openapi"] = "3.0.0"
    
    # Fix anyOf with null type issues - convert to nullable
    def fix_schema(schema: Any) -> Any:
        """Recursively fix anyOf schemas with null type."""
        if isinstance(schema, dict):
            # Check if this is an anyOf with null type
            if "anyOf" in schema:
                any_of = schema["anyOf"]
                if isinstance(any_of, list) and len(any_of) == 2:
                    # Check if one is null type
                    null_index = None
                    type_index = None
                    for i, item in enumerate(any_of):
                        if isinstance(item, dict):
                            if item.get("type") == "null":
                                null_index = i
                            elif "type" in item and item["type"] != "null":
                                type_index = i
                    
                    # If we found both null and a type, convert to nullable
                    if null_index is not None and type_index is not None:
                        type_schema = any_of[type_index].copy()
                        type_schema["nullable"] = True
                        # Copy other properties from the original schema
                        new_schema = {k: v for k, v in schema.items() if k != "anyOf"}
                        new_schema.update(type_schema)
                        schema = new_schema
            
            # Recursively fix nested schemas, including properties
            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    # Fix properties within schemas
                    for prop_name, prop_schema in value.items():
                        schema[key][prop_name] = fix_schema(prop_schema)
                else:
                    schema[key] = fix_schema(value)
        elif isinstance(schema, list):
            schema = [fix_schema(item) for item in schema]
        
        return schema
    
    # Fix all schemas in the OpenAPI spec
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        for schema_name, schema_def in openapi_schema["components"]["schemas"].items():
            openapi_schema["components"]["schemas"][schema_name] = fix_schema(schema_def)
    
    # Fix parameter schemas and response schemas
    if "paths" in openapi_schema:
        for path, methods in openapi_schema["paths"].items():
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    # Fix parameters
                    if "parameters" in operation:
                        for param in operation["parameters"]:
                            if "schema" in param:
                                param["schema"] = fix_schema(param["schema"])
                    # Fix request body schemas
                    if "requestBody" in operation and "content" in operation["requestBody"]:
                        for content_type, content_schema in operation["requestBody"]["content"].items():
                            if "schema" in content_schema:
                                content_schema["schema"] = fix_schema(content_schema["schema"])
                    # Fix response schemas
                    if "responses" in operation:
                        for status_code, response in operation["responses"].items():
                            if "content" in response:
                                for content_type, content_schema in response["content"].items():
                                    if "schema" in content_schema:
                                        content_schema["schema"] = fix_schema(content_schema["schema"])
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def register_exception_handlers(app: FastAPI):
    """Register global exception handlers."""
    
    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "type": "EntityNotFoundError"}
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "type": "ValidationError", "field": exc.field}
        )
    
    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "type": "ConflictError"}
        )
    
    @app.exception_handler(ApplicationException)
    async def application_exception_handler(request: Request, exc: ApplicationException):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc), "type": "ApplicationException"}
        )

def main()->FastAPI:
    builder=(Builder()
    .with_title("Notification Service")
    .with_description("Service for sending notifications via email and SMS")
    .with_version("1.0.0")
    .with_lifespan(lifespan))
    builder._openapi_url="/openapi.json"
    builder._docs_url="/docs"
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
    
    # Register global exception handlers
    register_exception_handlers(app)
    
    # Override OpenAPI schema generation to fix version and anyOf issues
    app.openapi = lambda: custom_openapi(app)
    
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
    processMessageUseCase = get_service(app, ProcessMessageUseCase)
    rabbitClient = get_service(app, IMessageConsumer)
    tenantservice.rabbitmqConsumer = rabbitClient
   # create rabbit client and adapter
    adapterConsumer =NotificationRabbitMQConsumer(
        rabbitmqConsumer=rabbitClient,
        tenantService=tenantservice
    )

    # connect, ensure queues for active tenants, subscribe and start consuming
    task = asyncio.create_task(adapterConsumer.startConsuming())

    try:
        yield
    finally:
        # Shutdown actions
        await adapterConsumer.stopConsuming()
        db.disconnect()
        
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("notification_service.main:main",factory=True, host="0.0.0.0", port=8000)