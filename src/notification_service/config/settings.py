from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "notification-service"
    app_env: str = "development"
    debug: bool = True

    # Database (async)
    database_url: str

    # Redis
    redis_url: str = "redis://:@localhost:6379/0"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    class Config:
        env_file = "../../.env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
