from logging.config import fileConfig
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context

# Ensure project's src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from notification_service.config.settings import settings

# Stub modules that break imports during Alembic env load
sys.modules["notification_service.infrastructure.cache.redis_cache"] = type(sys)("redis_cache")
sys.modules["notification_service.infrastructure.cache.redis_cache"].RedisCache = None

from notification_service.infrastructure.persistence.models.base import Base

from notification_service.infrastructure.persistence.models.email.email_notification import EmailNotificationModel  # noqa: F401
from notification_service.infrastructure.persistence.models.email.email_outbox import EmailOutboxModel  # noqa: F401
from notification_service.infrastructure.persistence.models.email.email_template import EmailTemplateModel  # noqa: F401
from notification_service.infrastructure.persistence.models.sms.sms_notification import SMSNotificationModel  # noqa: F401
from notification_service.infrastructure.persistence.models.sms.sms_outbox import SmsOutboxModel  # noqa: F401
from notification_service.infrastructure.persistence.models.sms.sms_template import SmsTemplateModel  # noqa: F401
from notification_service.infrastructure.persistence.models.in_app.in_app_notification import InAppNotificationModel  # noqa: F401
from notification_service.infrastructure.persistence.models.in_app.in_app_outbox import InAppOutboxModel  # noqa: F401
from notification_service.infrastructure.persistence.models.in_app.in_app_template import InAppTemplateModel  # noqa: F401
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel  # noqa: F401
from notification_service.infrastructure.persistence.models.tenant.tenant_email_configuration import TenantEmailConfigurationModel  # noqa: F401
from notification_service.infrastructure.persistence.models.tenant.tenant_sms_configuration import TenantSMSConfigurationModel  # noqa: F401
from notification_service.infrastructure.persistence.models.tenant.tenant_inapp_configuration import TenantInAppConfigurationModel  # noqa: F401
# from notification_service.infrastructure.persistence.models.tenant.tenant_telegram_configuration import TenantTelegramConfigurationModel  # noqa: F401
from notification_service.infrastructure.persistence.models.user.user import UserModel  # noqa: F401
from notification_service.infrastructure.persistence.models.user.user_tenant import UserTenantModel  # noqa: F401
# Telegram channel models — must be imported so Alembic autogenerate detects the tables
# from notification_service.infrastructure.persistence.models.telegram.telegram_template import TelegramTemplateModel  # noqa: F401
# from notification_service.infrastructure.persistence.models.telegram.telegram_notification import TelegramNotificationModel  # noqa: F401
# from notification_service.infrastructure.persistence.models.telegram.telegram_outbox import TelegramOutboxModel  # noqa: F401

# Sync URL for Alembic — never use config.set_main_option: ConfigParser rejects % in URL-encoded passwords.
sync_db_url = os.getenv("DATABASE_URL_SYNC") or settings.database_url.replace("+asyncpg", "")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=sync_db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(sync_db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
