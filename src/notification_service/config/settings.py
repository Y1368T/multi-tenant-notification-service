from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "notification-service"
    app_env: str = "development"
    debug: bool = True

    # Database (async) - defaults to host.docker.internal for Docker environment
    database_url: str = "postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/qena_notification_service_db"

    # Redis - defaults to redis service name for Docker environment
    redis_url: str = "redis://:@redis:6379/0"

    # RabbitMQ - defaults to rabbitmq service name for Docker environment
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    class Config:
        env_file = "../../.env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
