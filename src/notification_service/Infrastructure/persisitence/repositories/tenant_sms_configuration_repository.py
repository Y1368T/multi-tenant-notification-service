"""Tenant SMS configuration repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persisitence.models.tenant.tenant_sms_configuration import TenantSMSConfigurationModel
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.infrastructure.persisitence.mappers.tenant_sms_configuration_mapper import TenantSmsConfigurationMapper

class TenantSmsConfigurationRepository(GenericRepository[TenantSMSConfigurationModel, TenantSMSConfiguration]):
    """Repository for tenant SMS configurations."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, TenantSMSConfigurationModel, TenantSmsConfigurationMapper())
