from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ensure project's src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import settings
from notification_service.config.settings import settings

# Import Base and all models directly - this WILL trigger package imports,
# but we'll temporarily disable the problematic ones
import sys

# Temporarily stub out empty modules that cause import errors
sys.modules['notification_service.infrastructure.cache.redis_cache'] = type(sys)('redis_cache')
sys.modules['notification_service.infrastructure.cache.redis_cache'].RedisCache = None

# Now we can import from the proper package structure
from notification_service.infrastructure.persistence.models.base import Base

# Import all model files - they must be imported to register with Base.metadata
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
# Set sqlalchemy url from settings (use sync URL for Alembic)
sync_db_url = os.getenv('DATABASE_URL_SYNC')
config.set_main_option('sqlalchemy.url', sync_db_url)

# target metadata for 'autogenerate'
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
