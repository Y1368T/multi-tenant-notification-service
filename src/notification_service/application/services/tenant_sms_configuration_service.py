from typing import Optional, Dict, List, Any
from uuid import UUID
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.infrastructure.providers.sms.afromessage_provider import AfromessageSMSProvider
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.tenant_sms_confuguration_request_dto import TenantSMSConfigurationResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter
)
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.application.services.base_service import BaseService


class TenantSMSConfigurationService(BaseService[TenantSMSConfiguration, TenantSMSConfigurationResponseDTO]):

    def __init__(self, uow: IUnitOfWork, afro_service: AfromessageSMSProvider):
        super().__init__(uow, TenantSMSConfiguration, TenantSMSConfigurationResponseDTO)
        self.uow = uow
        self._handlers = {
            SMSProvider.AFROMESSAGE: afro_service
        }
    
    def _get_repository(self):
        """Get tenant SMS configurations repository."""
        return self.uow.tenantSmsConfigurations
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'providerName') and params.providerName:
            filters["providerName"] = params.providerName
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for tenant SMS configurations."""
        # Tenant SMS configurations don't have related filters by default
        return []

    async def getConfigurationByTenantId(self, tenantId: UUID) -> TenantSMSConfiguration:
        """Retrieve SMS configuration for a given tenant.
        
        Args:
            tenantId: Tenant identifier

        Returns:
            TenantSMSConfiguration object if found, None otherwise
        """
        async with self.uow:
            config = await self.uow.tenantSmsConfigurations.find(lambda x:x.tenantId==tenantId)
            return config
    # Keep old methods for backward compatibility
    async def createConfiguration(self, config: TenantSMSConfiguration) -> TenantSMSConfiguration:
        """Create a new SMS configuration (deprecated - use create() instead)."""
        return await self.create(config)
    
    # Keep old methods for backward compatibility
    async def updateConfiguration(self, config: TenantSMSConfiguration) -> TenantSMSConfiguration:
        """Update an existing SMS configuration (deprecated - use update() instead)."""
        return await self.update(config)
    
    async def deleteConfiguration(self, configId: UUID) -> None:
        """Delete an existing SMS configuration (deprecated - use delete() instead)."""
        await self.delete(configId)
            
    async def getConfigurationById(self, configId: UUID) -> Optional[TenantSMSConfiguration]:
        """Retrieve SMS configuration by its ID (custom method)."""
        async with self.uow:
            config = await self.uow.tenantSmsConfigurations.getById(configId)
            return config
        
    async def doACircuitBreakerCheck(self, config: TenantSMSConfiguration, provider: SMSProvider) -> bool:
        """Perform a circuit breaker check for SMS configurations.
        
        Returns:
            bool: True if the circuit is closed, False if open
        """
        # Placeholder implementation for circuit breaker logic
        
        match provider:
            case SMSProvider.AFROMESSAGE:
                # Implement Afromessage-specific circuit breaker logic
                return await self._handlers[provider].circuit_breaker_check(config)
            case _:
                return False
        return False
    # Keep old method for backward compatibility
    async def getAllConfigurationsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[TenantSMSConfigurationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        return await self.get(req)