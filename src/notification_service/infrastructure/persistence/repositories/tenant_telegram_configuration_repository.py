from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.tenant.tenant_telegram_configuration import TenantTelegramConfigurationModel
from notification_service.domain.entities.tenant.tenant_telegram_configuration import TenantTelegramConfiguration
from notification_service.infrastructure.persistence.mappers.tenant_telegram_configuration_mapper import TenantTelegramConfigurationMapper


class TenantTelegramConfigurationRepository(GenericRepository[TenantTelegramConfigurationModel, TenantTelegramConfiguration]):
    """Repository for Tenant Telegram Configurations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TenantTelegramConfigurationModel, TenantTelegramConfigurationMapper())
