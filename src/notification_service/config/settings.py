from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # goes up to notification-service/


class Settings(BaseSettings):
    # App settings with defaults
    app_name: str = "notification"
    app_env: str = "development"
    debug: bool = True

    # Database (async) - default for local development
    # When running in Docker, this is overridden by DATABASE_URL env var
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/qena_notification_service_db"

    # Redis - default for local development
    redis_url: str = "redis://:@localhost:6379/10"

    # RabbitMQ - default for local development
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    enable_customer_language_rpc: bool = True
    customer_rpc_queue: str = "NotificationCustomerManagementRPC"
    customer_rpc_timeout: float = 5.0
    
    # Security settings
    admin_api_key: Optional[str] = None  # Admin API key for bypassing tenant authentication
    
    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False  # Allow DATABASE_URL or database_url
        extra = "allow"  # Allow extra fields


@lru_cache()
def getSettings() -> Settings:
    return Settings()


settings = getSettings()
