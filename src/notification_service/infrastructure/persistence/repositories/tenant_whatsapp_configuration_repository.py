"""Tenant WhatsApp configuration repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.infrastructure.persistence.repositories.generic_repository import GenericRepository
from notification_service.infrastructure.persistence.models.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfigurationModel
from notification_service.domain.entities.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfiguration
from notification_service.infrastructure.persistence.mappers.tenant_whatsapp_configuration_mapper import TenantWhatsAppConfigurationMapper

class TenantWhatsAppConfigurationRepository(GenericRepository[TenantWhatsAppConfigurationModel, TenantWhatsAppConfiguration]):
    """Repository for tenant WhatsApp configurations."""
    def __init__(self, session: AsyncSession):
        super().__init__(session, TenantWhatsAppConfigurationModel, TenantWhatsAppConfigurationMapper())
