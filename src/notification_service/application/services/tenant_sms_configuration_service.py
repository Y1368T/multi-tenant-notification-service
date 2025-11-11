from typing import Optional, Dict
from uuid import UUID
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.infrastructure.providers.sms.ethiotelecom_shortcode import EthioTelecomShortcodeSMSProvider
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.tenant_sms_confuguration_request_dto import TenantSMSConfigurationResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO


class TenantSMSConfigurationService:


    def __init__(self, uow:IUnitOfWork, ethio_service:EthioTelecomShortcodeSMSProvider):
        self.uow = uow
        self._handlers = {
            SMSProvider.ETHIOTELECOM: ethio_service
        }

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
    async def createConfiguration(self, config: TenantSMSConfiguration) -> TenantSMSConfiguration:
        """Create a new SMS configuration for a tenant.
        
        Args:
            config: TenantSMSConfiguration entity to create

        Returns:
            Created TenantSMSConfiguration entity
        """
        async with self.uow:
            createdConfig = await self.uow.tenantSmsConfigurations.add(config)
            await self.uow.commit()
            return createdConfig
        
    async def updateConfiguration(self, config: TenantSMSConfiguration) -> TenantSMSConfiguration:
        """Update an existing SMS configuration for a tenant.

        Args:
            config: TenantSMSConfiguration entity with updated values

        Returns:
            Updated TenantSMSConfiguration entity
        """
        async with self.uow:
            updatedConfig = await self.uow.tenantSmsConfigurations.update(config)
            await self.uow.commit()
            return updatedConfig
        
    async def deleteConfiguration(self, configId: UUID) -> None:
        """Delete an existing SMS configuration for a tenant.

        Args:
            configId: TenantSMSConfiguration identifier
        """
        async with self.uow:
            await self.uow.tenantSmsConfigurations.delete(configId)
            await self.uow.commit()
            
    async def getConfigurationById(self, configId: UUID) -> Optional[TenantSMSConfiguration]:
        """Retrieve SMS configuration by its ID.
        
        Args:
            configId: TenantSMSConfiguration identifier

        Returns:
            TenantSMSConfiguration entity if found, None otherwise
        """
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
            case SMSProvider.ETHIOTELECOM:
                # Implement EthioTelecom-specific circuit breaker logic
               return self._handlers[provider].circuit_breaker_check(config)
            case SMSProvider.AFROMESSAGE:
               return self._handlers[provider].circuit_breaker_check(config)
            case _:
                return False
        return False
    async def getAllConfigurationsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[TenantSMSConfigurationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        """
        async with self.uow:
            
            relatedFiltersTuples = [
            (rf.relationshipPath, rf.field, rf.op.value if hasattr(rf.op, 'value') else str(rf.op), rf.value)
            for rf in (req.relatedFilters or [])
            ]
            result = await self.uow.tenantSmsConfigurations.listAdvancedPaginated(
                page=req.page,
                pageSize=req.pageSize,
                rootFilters=req.filters or {},
                relatedFilters=relatedFiltersTuples,
                includes=[],
                sortBy=req.sortBy,
                sortDirection=req.sortDirection.value,
                searchText=req.searchText,
                searchFields=req.searchFields or []
            )

            dtoItems = [
                TenantSMSConfigurationResponseDTO.fromEntityWithRelations(config)
                for config in result.items
            ]

            return PaginatedResponseDTO(
                items=dtoItems,
                page=result.page,
                pageSize=result.pageSize,
                totalCount=result.totalCount,
                totalPages=result.totalPages,
                hasNext=result.hasNext,
                hasPrevious=result.hasPrevious
            )