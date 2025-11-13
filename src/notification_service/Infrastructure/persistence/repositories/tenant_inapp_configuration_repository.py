from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.tenant.tenant_inapp_configuration import TenantInAppConfigurationModel
from notification_service.domain.entities.tenant.tenant_inapp_configuration import TenantInAppConfiguration
from notification_service.infrastructure.persistence.mappers.tenant_inapp_configuration_mapper import TenantInAppConfigurationMapper

class TenantInAppConfigurationRepository(GenericRepository[TenantInAppConfigurationModel, TenantInAppConfiguration]):
    """Repository for tenant in-app configurations."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, TenantInAppConfigurationModel, TenantInAppConfigurationMapper())
