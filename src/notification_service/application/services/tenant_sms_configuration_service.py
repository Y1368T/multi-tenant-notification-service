from typing import Optional, Dict, List, Any
from uuid import UUID
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.value_objects.providers import SMSProvider
from notification_service.infrastructure import RedisCache
from notification_service.infrastructure.providers.sms.afromessage_provider import AfromessageSMSProvider
from notification_service.infrastructure.providers.sms.kannel_sms_provider import KannelSMSProvider
from notification_service.infrastructure.providers.sms.jasmin_sms_provider import JasminSMSProvider
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.tenant_sms_confuguration_request_dto import TenantSMSConfigurationResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter
)
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.application.services.base_service import BaseService
from notification_service.shared.exceptions.application_exceptions import ApplicationException, EntityNotFoundError
import logging

logger = logging.getLogger(__name__)
class TenantSMSConfigurationService(BaseService[TenantSMSConfiguration, TenantSMSConfigurationResponseDTO]):

    def __init__(
        self,
        uow: IUnitOfWork,
        afro_service: AfromessageSMSProvider,
        kannel_service: KannelSMSProvider,
        jasmin_service: JasminSMSProvider,
        redis: RedisCache,
    ):
        super().__init__(uow, TenantSMSConfiguration, TenantSMSConfigurationResponseDTO)
        self.uow = uow
        self._handlers = {
            SMSProvider.AFROMESSAGE: afro_service,
            SMSProvider.KANNEL: kannel_service,
            SMSProvider.JASMIN: jasmin_service,
        }
        self.redis = redis
    
    def _get_repository(self):
        """Get tenant SMS configurations repository."""
        return self.uow.tenantSmsConfigurations
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for tenant SMS configurations."""
        # Tenant SMS configurations don't have related filters by default
        return []
    
    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for tenant SMS configurations."""
        return ["providerName"]
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for tenant SMS configurations."""
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                root_filters['id'] = UUID(params.id) if isinstance(params.id, str) else params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id
        
        if hasattr(params, 'tenantId') and params.tenantId:
            try:
                tenant_id_value = UUID(params.tenantId) if isinstance(params.tenantId, str) else params.tenantId
                root_filters['tenantId'] = tenant_id_value
            except (ValueError, AttributeError):
                root_filters['tenantId'] = params.tenantId
        
        # Extract custom filters
        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)
        
        # Build related filters
        related_filters = self._build_related_filters(params)
        
        # Get search fields
        search_fields = self._get_search_fields()
        
        # Build and return PaginatedRequest
        return PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=search_fields,
            filters=root_filters,
            relatedFilters=related_filters
        )

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
        try:
            async with self.uow:
                created_config = await self.uow.tenantSmsConfigurations.create(config)
                await self.uow.commit()
                cache_key = f"tenant_config:sms:{config.tenantId}"
                await self.redis.set(cache_key, created_config.__dict__, expire=60*60*24)
                return created_config
        except Exception as e:
            raise ApplicationException(
                f"Error creating SMS configuration: {e}",
                code="ERROR_CREATING_SMS_CONFIGURATION",
                details={"config": config}
            )
        finally:
            if config:
                cache_key = f"tenant_config:sms:{config.tenantId}"
                await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                return config
    
    # Keep old methods for backward compatibility
    async def updateConfiguration(self, config: TenantSMSConfiguration) -> TenantSMSConfiguration:
        """Update an existing SMS configuration (deprecated - use update() instead)."""
        try:
            async with self.uow:
                updated_config = await self.uow.tenantSmsConfigurations.update(config)
                await self.uow.commit()
                cache_key = f"tenant_config:sms:{config.tenantId}"
                await self.redis.delete(cache_key)
                await self.redis.set(cache_key, updated_config.__dict__, expire=60*60*24)
                return updated_config
        except Exception as e:
            raise ApplicationException(
                f"Error updating SMS configuration: {e}",
                code="ERROR_UPDATING_SMS_CONFIGURATION",
                details={"configId": config.id}
            )
        finally:
            if config:
                cache_key = f"tenant_config:sms:{config.tenantId}"
                await self.redis.delete(cache_key)
                await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                return config
    
    async def deleteConfiguration(self, configId: UUID) -> None:
        """Delete an existing SMS configuration (deprecated - use delete() instead)."""
        
        async with self.uow:
            try:
                config = await self.uow.tenantSmsConfigurations.getById(configId)
                if config:
                    cache_key = f"tenant_config:sms:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    await self.uow.tenantSmsConfigurations.delete(configId)
                    await self.uow.commit()
            except Exception as e:
                logger.error(f"Error deleting SMS configuration: {e}")
                raise ApplicationException(
                    f"Error deleting SMS configuration: {e}",
                    code="ERROR_DELETING_SMS_CONFIGURATION",
                    details={"configId": configId}
                )
            finally:
                if config:
                    cache_key = f"tenant_config:sms:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    return config

    async def partialUpdate(self, configId: UUID, updates: Dict[str, Any]) -> TenantSMSConfiguration:
        """Partial update of an existing SMS configuration (deprecated - use partialUpdate() instead)."""
        try:
            async with self.uow:
                config = await self.uow.tenantSmsConfigurations.getById(configId)
                if config:
                    cache_key = f"tenant_config:sms:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    await self.uow.tenantSmsConfigurations.partialUpdate(configId, updates)
                    await self.uow.commit()
                    await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                    return config
        except Exception as e:
            raise ApplicationException(
                f"Error partial updating SMS configuration: {e}",
                code="ERROR_PARTIAL_UPDATING_SMS_CONFIGURATION",
                details={"configId": configId}
            )
        finally:
            if config:
                cache_key = f"tenant_config:sms:{config.tenantId}"
                await self.redis.delete(cache_key)
                await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                return config
            
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
            case SMSProvider.KANNEL:
                # Placeholder: implement Kannel-specific circuit breaker logic if needed
                return True
            case SMSProvider.JASMIN:
                # Placeholder: implement Jasmin-specific circuit breaker logic if needed
                return True
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