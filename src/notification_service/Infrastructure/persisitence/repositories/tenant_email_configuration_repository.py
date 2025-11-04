"""Tenant email configuration repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.Infrastructure.persisitence.models.tenant.tenant_email_configuration import TenantEmailConfigurationModel
from notification_service.domain.entities.tenant.tenant_email_configuration import TenantEmailConfiguration
from notification_service.Infrastructure.persisitence.mappers.tenant_email_configuration_mapper import TenantEmailConfigurationMapper

class TenantEmailConfigurationRepository(GenericRepository[TenantEmailConfigurationModel, TenantEmailConfiguration]):
    """Repository for tenant email configurations."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, TenantEmailConfigurationModel, TenantEmailConfigurationMapper())
