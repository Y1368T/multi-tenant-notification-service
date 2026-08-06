from contextlib import asynccontextmanager
import logging
from notification_service.infrastructure.cache.redis_cache import RedisCache
from qena_shared_lib.application import Builder
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.messaging.rabbitmq import RabbitMQConsumer, RabbitMQRPCClient
from notification_service.application.use_cases.process_message_usecase import ProcessMessageUseCase
from notification_service.application.services import tenant_service
from notification_service.adapters.inbound.rabbitmq.rabbitmq_consumer import NotificationRabbitMQConsumer
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
import asyncio
import types
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.rest.routers import register_controllers
from notification_service.config.settings import Settings
from qena_shared_lib.dependencies.http import get_service
from notification_service.application.services import in_app_notification_service
from notification_service.application.services import tenant_sms_configuration_service
from notification_service.application.services import in_app_template_service
from notification_service.application.services import sms_notification_service
from notification_service.application.services import tenant_inapp_configuration_service
from notification_service.domain.interfaces.imessage_consumer import IMessageConsumer
from notification_service.domain.interfaces.imessage_handler import IMessageHandler
from notification_service.application.services import sms_outbox_service
from notification_service.application.handlers.message_router import MessageRouter
from notification_service.application.services import in_app_outbox_service
from notification_service.domain.interfaces.ichannel_handler import IChannelHandler
from notification_service.application.handlers.sms_channel_handler import SMSChannelHandler
from notification_service.infrastructure.providers.sms.afromessage_provider import AfromessageSMSProvider
from notification_service.application.services.sms_template_service import SMSTemplateService
from notification_service.infrastructure.providers.sms.kifiyaSmsProvider import KifiyaSMSProvider
from notification_service.infrastructure.providers.sms.jasmin_sms_provider import JasminSMSProvider
from notification_service.infrastructure.providers.in_app.fcm_provider import FCMProvider
from notification_service.application.handlers.in_app_channel_handler import InAppChannelHandler
# Email imports
from notification_service.application.handlers.email_channel_handler import EmailChannelHandler
from notification_service.infrastructure.providers.email.smtp_provider import SMTPProvider
from notification_service.application.services.email_notification_service import EmailNotificationService
from notification_service.application.services.email_template_service import EmailTemplateService
from notification_service.application.services.email_outbox_service import EmailOutboxService
from notification_service.application.services.tenant_email_configuration import TenantEmailConfigurationService
from notification_service.application.services.provider_service import ProviderService
from notification_service.domain.interfaces.imessage_consumer import IMessageConsumer
from notification_service.infrastructure.services.customer_service_client import CustomerServiceClient
from notification_service.infrastructure.services.webhook_client import WebhookClient
from notification_service.infrastructure.persistence.seeds.provider_seed import seed_providers
from notification_service.infrastructure.jobs.outbox_processor import OutboxProcessor
# Telegram services
from notification_service.application.services.telegram_template_service import TelegramTemplateService
from notification_service.application.services.telegram_notification_service import TelegramNotificationService
from notification_service.application.services.telegram_outbox_service import TelegramOutboxService
from notification_service.application.services.tenant_telegram_configuration_service import TenantTelegramConfigurationService
from notification_service.application.services.auth_service import AuthService
from notification_service.infrastructure.services.keycloak_client import KeycloakClient
from notification_service.domain.interfaces.ikeycloak_client import IKeycloakClient


from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from typing import Any, Dict
from notification_service.shared.exceptions.application_exceptions import (
    ApplicationException,
    EntityNotFoundError,
    ValidationError,
    ConflictError,
    UnauthorizedError,
    InvalidAPIKeyError
)
from notification_service.infrastructure.providers.telegram.telegram_provider import TelegramProvider
from notification_service.application.handlers.telegram_channel_handler import TelegramChannelHandler
from sqlalchemy.exc import IntegrityError
import logging
import sys

# Configure logging FIRST, before anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    ],
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)

def customOpenapi(app: FastAPI) -> Dict[str, Any]:
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
    openapi_schema["openapi"] = "3.0.3"
    
    # Fix anyOf with null type issues - convert to nullable
    def fixSchema(schema: Any) -> Any:
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
                        schema[key][prop_name] = fixSchema(prop_schema)
                else:
                    schema[key] = fixSchema(value)
        elif isinstance(schema, list):
            schema = [fixSchema(item) for item in schema]
        
        return schema
    
    # Fix all schemas in the OpenAPI spec
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        for schema_name, schema_def in openapi_schema["components"]["schemas"].items():
            openapi_schema["components"]["schemas"][schema_name] = fixSchema(schema_def)
    
    # Fix parameter schemas and response schemas
    if "paths" in openapi_schema:
        for path, methods in openapi_schema["paths"].items():
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    # Fix parameters
                    if "parameters" in operation:
                        for param in operation["parameters"]:
                            if "schema" in param:
                                param["schema"] = fixSchema(param["schema"])
                    # Fix request body schemas
                    if "requestBody" in operation and "content" in operation["requestBody"]:
                        for content_type, content_schema in operation["requestBody"]["content"].items():
                            if "schema" in content_schema:
                                content_schema["schema"] = fixSchema(content_schema["schema"])
                    # Fix response schemas
                    if "responses" in operation:
                        for status_code, response in operation["responses"].items():
                            if "content" in response:
                                for content_type, content_schema in response["content"].items():
                                    if "schema" in content_schema:
                                        content_schema["schema"] = fixSchema(content_schema["schema"])
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def registerExceptionHandlers(app: FastAPI):
    """Register global exception handlers with standardized error format."""
    
    logger = logging.getLogger(__name__)
    
    @app.exception_handler(RequestValidationError)
    async def requestValidationErrorHandler(request: Request, exc: RequestValidationError):
        """
        Handle FastAPI/Pydantic request validation errors.
        Converts to standardized error format.
        """
        logger.error(f"RequestValidationError: {exc}", exc_info=True)
        
        # Extract validation errors from Pydantic format
        errors = exc.errors()
        
        # Build a consolidated message and details
        error_messages = []
        field_errors = []
        
        for error in errors:
            # Get field path (e.g., ["body", "prefered_communication_method"] -> "prefered_communication_method")
            field_path = ".".join(str(loc) for loc in error.get("loc", []))
            # Remove "body." prefix if present
            if field_path.startswith("body."):
                field_path = field_path[5:]
            
            error_type = error.get("type", "validation_error")
            error_msg = error.get("msg", "Validation error")
            error_input = error.get("input")
            
            # Create a user-friendly message
            if field_path:
                user_message = f"{field_path}: {error_msg}"
            else:
                user_message = error_msg
            
            error_messages.append(user_message)
            
            # Store field-specific error details
            field_errors.append({
                "field": field_path if field_path else None,
                "message": error_msg,
                "type": error_type,
                "input": error_input
            })
        
        # Create a consolidated message
        if len(error_messages) == 1:
            consolidated_message = error_messages[0]
        else:
            consolidated_message = f"Validation failed for {len(error_messages)} field(s): " + "; ".join(error_messages)
        
        # Create standardized error response
        from notification_service.shared.exceptions.application_exceptions import ValidationError
        validation_exc = ValidationError(
            message=consolidated_message,
            code="REQUEST_VALIDATION_ERROR",
            details={
                "errors": field_errors,
                "field_count": len(field_errors)
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=validation_exc.to_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY)
        )
    
    @app.exception_handler(EntityNotFoundError)
    async def entityNotFoundHandler(request: Request, exc: EntityNotFoundError):
        logger.error(f"EntityNotFoundError: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=exc.to_error_response(status.HTTP_404_NOT_FOUND)
        )
    
    @app.exception_handler(ValidationError)
    async def validationErrorHandler(request: Request, exc: ValidationError):
        logger.error(f"ValidationError: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=exc.to_error_response(status.HTTP_400_BAD_REQUEST)
        )
    
    @app.exception_handler(ConflictError)
    async def conflictErrorHandler(request: Request, exc: ConflictError):
        logger.error(f"ConflictError: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_error_response(status.HTTP_409_CONFLICT)
        )
    
    @app.exception_handler(IntegrityError)
    async def integrityErrorHandler(request: Request, exc: IntegrityError):
        """
        Handle database integrity constraint violations.
        Converts SQLAlchemy IntegrityError to standardized format.
        """
        logger.error(f"Database integrity error: {exc}", exc_info=True)
        
        # Extract constraint name and details from the error
        error_message = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        # Extract the meaningful detail message (the part after "DETAIL: ")
        detail_message = None
        if "DETAIL:" in error_message:
            detail_parts = error_message.split("DETAIL:", 1)
            if len(detail_parts) > 1:
                detail_message = detail_parts[1].strip()
        
        # Determine error code and message based on constraint type
        if "unique constraint" in error_message.lower() or "duplicate key" in error_message.lower():
            code = "DUPLICATE_ENTRY"
            message = "A record with this value already exists. Please use a unique value."
        elif "foreign key constraint" in error_message.lower():
            code = "FOREIGN_KEY_VIOLATION"
            message = "Referenced record does not exist. Please check related entities."
        elif "not null constraint" in error_message.lower():
            code = "NOT_NULL_VIOLATION"
            message = "Required field cannot be null."
        else:
            code = "DATABASE_CONSTRAINT_VIOLATION"
            message = "Database constraint violation occurred."
        
        # Build details with the extracted meaningful message
        details = {}
        if detail_message:
            details["message"] = detail_message
        
        conflict_exc = ConflictError(
            message=message,
            code=code,
            details=details
        )
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=conflict_exc.to_error_response(status.HTTP_409_CONFLICT)
        )
    
    @app.exception_handler(ValueError)
    async def valueErrorHandler(request: Request, exc: ValueError):
        """
        Handle ValueError exceptions (including built-in Python ValueError).
        Converts to standardized format.
        """
        logger.error(f"ValueError: {exc}", exc_info=True)
        
        # Check if it's our custom ValueError or built-in
        if isinstance(exc, ApplicationException):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=exc.to_error_response(status.HTTP_400_BAD_REQUEST)
            )
        else:
            # Handle built-in ValueError
            from notification_service.shared.exceptions.application_exceptions import ValueError as CustomValueError
            custom_exc = CustomValueError(
                message=str(exc),
                code="VALUE_ERROR"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=custom_exc.to_error_response(status.HTTP_400_BAD_REQUEST)
            )
    
    @app.exception_handler(UnauthorizedError)
    async def unauthorizedErrorHandler(request: Request, exc: UnauthorizedError):
        """Handle unauthorized access errors (401)."""
        logger.warning(f"UnauthorizedError: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=exc.to_error_response(status.HTTP_401_UNAUTHORIZED)
        )
    
    @app.exception_handler(InvalidAPIKeyError)
    async def invalidAPIKeyErrorHandler(request: Request, exc: InvalidAPIKeyError):
        """Handle invalid API key errors (401)."""
        logger.warning(f"InvalidAPIKeyError: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=exc.to_error_response(status.HTTP_401_UNAUTHORIZED)
        )
    
    @app.exception_handler(ApplicationException)
    async def applicationExceptionHandler(request: Request, exc: ApplicationException):
        logger.error(f"ApplicationException: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=exc.to_error_response(status.HTTP_500_INTERNAL_SERVER_ERROR)
        )
    
    @app.exception_handler(Exception)
    async def generalExceptionHandler(request: Request, exc: Exception):
        """Catch-all handler for any unhandled exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        from notification_service.shared.exceptions.application_exceptions import ApplicationException
        app_exc = ApplicationException(
            message="An unexpected error occurred. Please try again later.",
            code="INTERNAL_SERVER_ERROR",
            details={"original_error": str(exc)}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=app_exc.to_error_response(status.HTTP_500_INTERNAL_SERVER_ERROR)
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
    builder.with_singleton(RedisCache)
    builder.with_singleton(RabbitMQRPCClient)
    builder.with_singleton(CustomerServiceClient)
    builder.with_singleton(WebhookClient)
    builder.with_transient(IUnitOfWork,UnitOfWork)
    # SMS Providers
    builder.with_transient(AfromessageSMSProvider)
    builder.with_transient(KifiyaSMSProvider)
    builder.with_transient(JasminSMSProvider)
    # In-App Providers
    builder.with_transient(FCMProvider)
    # Email Providers
    builder.with_transient(SMTPProvider)
    # Telegram Providers
    builder.with_transient(TelegramProvider)
    builder.with_transient(ProcessMessageUseCase)
    # Register concrete channel handlers directly (MessageRouter needs concrete types)
    builder.with_transient(SMSChannelHandler)
    builder.with_transient(InAppChannelHandler)
    builder.with_transient(EmailChannelHandler)
    builder.with_transient(TelegramChannelHandler)
    builder.with_transient(IMessageHandler,MessageRouter)
    # Register TenantService as singleton so rabbitmqConsumer can be set at startup
    # and reused when creating tenants via API
    builder.with_singleton(tenant_service.TenantService)
    builder.with_singleton(IMessageConsumer, RabbitMQConsumer)
    # SMS Services
    builder.with_transient(tenant_sms_configuration_service.TenantSMSConfigurationService)
    builder.with_transient(sms_notification_service.SMSNotificationService)
    builder.with_transient(sms_outbox_service.SMSOutboxService)
    builder.with_transient(SMSTemplateService)
    # In-App Services
    builder.with_transient(in_app_notification_service.InAppNotificationService)
    builder.with_transient(in_app_template_service.InAppTemplateService)
    builder.with_transient(tenant_inapp_configuration_service.TenantInAppConfigurationService)
    builder.with_transient(in_app_outbox_service.InAppOutboxService)
    # Email Services
    builder.with_transient(EmailNotificationService)
    builder.with_transient(EmailTemplateService)
    builder.with_transient(EmailOutboxService)
    builder.with_transient(TenantEmailConfigurationService)
    # Provider Service
    builder.with_transient(ProviderService)
    # Telegram Services
    builder.with_transient(TelegramTemplateService)
    builder.with_transient(TelegramNotificationService)
    builder.with_transient(TelegramOutboxService)
    builder.with_transient(TenantTelegramConfigurationService)
    # Auth Services
    builder.with_singleton(IKeycloakClient, KeycloakClient)
    builder.with_transient(AuthService)

    
    logging.basicConfig(
    level=logging.INFO,  # Set to INFO to see info logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Output to console/docker logs
    ]
)
    
    app=builder.build()
    
    # Register global exception handlers
    registerExceptionHandlers(app)
    
    # Override OpenAPI schema generation to fix version and anyOf issues
    app.openapi = lambda: customOpenapi(app)
    
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
    try:
        await seed_providers(db)
    except Exception:
        logging.getLogger(__name__).exception("Failed to seed providers during startup.")
        raise
    redis=get_service(app,RedisCache)
    await redis.connect()
    tenantservice=get_service(app,tenant_service.TenantService)
    
    # Get ProcessMessageUseCase from DI container
    
    rabbitClient = get_service(app, IMessageConsumer)
    tenantservice.rabbitmqConsumer = rabbitClient

    settings=get_service(app,Settings)

    if settings.enable_customer_language_rpc:
        rpc_client = get_service(app, RabbitMQRPCClient)
        await rpc_client.connect()
   # create rabbit client and adapter
    adapterConsumer =NotificationRabbitMQConsumer(
        rabbitmqConsumer=rabbitClient,
        tenantService=tenantservice
    )

    # connect, ensure queues for active tenants, subscribe and start consuming
    rabbitmq_task = asyncio.create_task(adapterConsumer.startConsuming())
    
    # Create and start OutboxProcessor background worker
    # Build dependencies for OutboxProcessor
    database = get_service(app, Database)
    settings = get_service(app, Settings)
    webhook_client = get_service(app, WebhookClient)
    
    # Build SMS providers dictionary (provider_name -> provider instance)
    kifiya_provider = get_service(app, KifiyaSMSProvider)
    jasmin_provider = get_service(app, JasminSMSProvider)
    afromessage_provider = get_service(app, AfromessageSMSProvider)
    sms_providers = {
        "kifiya": kifiya_provider,
        "jasmin": jasmin_provider,
        "afromessage": afromessage_provider
    }
    
    # Get email and in-app providers
    email_provider = get_service(app, SMTPProvider)
    inapp_provider = get_service(app, FCMProvider)
    telegram_provider = get_service(app, TelegramProvider)
    
    # Create OutboxProcessor instance
    outbox_processor = OutboxProcessor(
        database=database,
        sms_providers=sms_providers,
        email_provider=email_provider,
        inapp_provider=inapp_provider,
        telegram_provider=telegram_provider,
        settings=settings,
        webhook_client=webhook_client
    )
    
    # Start background task
    outbox_task = asyncio.create_task(outbox_processor.start())
    logger.info("OutboxProcessor background task started")

    try:
        yield
    finally:
        # Shutdown actions
        logger.info("Shutting down OutboxProcessor...")
        outbox_processor.stop()
        
        await adapterConsumer.stopConsuming()
        await db.disconnect()
        await redis.disconnect()
        
        # Cancel both tasks
        rabbitmq_task.cancel()
        outbox_task.cancel()
        await asyncio.gather(rabbitmq_task, outbox_task, return_exceptions=True)
        
        if rpc_client:  # Use the variable from outer scope
            try:
                await rpc_client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting RPC client: {e}")
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("notification_service.main:main",factory=True, host="0.0.0.0", port=8000)