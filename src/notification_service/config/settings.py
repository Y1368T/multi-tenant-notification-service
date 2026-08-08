from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # goes up to notification-service/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # App settings with defaults
    app_name: str = "notification"
    app_env: str = "development"
    debug: bool = True

    # Database (async) - default for local development
    # When running in Docker, this is overridden by DATABASE_URL env var
    database_url: str = ""

    # Redis - default for local development
    redis_url: str = "redis://:@localhost:6379/10"

    # RabbitMQ - default for local development
    rabbitmq_url: str = "amqp://guest:guest@localhost:5673/"

    enable_customer_language_rpc: bool = True
    customer_rpc_queue: str = "NotificationCustomerManagementRPC"
    customer_rpc_timeout: float = 5.0
    
    # Security settings
    admin_api_key: Optional[str] = None  # Admin API key for bypassing tenant authentication
    session_signing_key: str = "default_unsafe_key_for_dev_only"  # Secret used for signing backend session tokens
    
    # Keycloak settings
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "mtns"
    keycloak_client_id: str = "mtns-backend"
    keycloak_client_secret: str = ""
    
    keycloak_admin_client_id: str = "admin-cli"
    keycloak_admin_client_secret: str = ""
    
    # Outbox retry settings
    outbox_poll_interval_seconds: int = 60  # Poll every 1 minute
    outbox_max_retries: int = 5  # Maximum retry attempts before marking as permanently failed
    outbox_base_retry_delay_minutes: int = 5  # Base delay for exponential backoff
    outbox_batch_size: int = 50  # Messages to process per poll cycle
    bulk_max_notifications: int = 1000  # Maximum notifications allowed per bulk request
    

@lru_cache()
def getSettings() -> Settings:
    return Settings()


settings = getSettings()
