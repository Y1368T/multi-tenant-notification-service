from typing import Optional, Dict, List, Any
from uuid import UUID
from notification_service.domain.entities.tenant.tenant_inapp_configuration import TenantInAppConfiguration
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.tenant_inapp_configuration_request_dto import TenantInAppConfigurationResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter
)
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.application.services.base_service import BaseService
from notification_service.infrastructure import RedisCache
from notification_service.shared.exceptions.application_exceptions import ApplicationException, EntityNotFoundError


class TenantInAppConfigurationService(BaseService[TenantInAppConfiguration, TenantInAppConfigurationResponseDTO]):

    def __init__(self, uow: IUnitOfWork, redis: RedisCache):
        super().__init__(uow, TenantInAppConfiguration, TenantInAppConfigurationResponseDTO)
        self.uow = uow
        self.redis = redis
    def _get_repository(self):
        """Get tenant in-app configurations repository."""
        return self.uow.tenantInAppConfigurations
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        if hasattr(params, 'providerName') and params.providerName:
            filters["providerName"] = params.providerName
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for tenant in-app configurations."""
        # Tenant in-app configurations don't have related filters by default
        return []
    
    def _get_search_fields(self) -> Optional[List[str]]:
        """Get search fields for tenant in-app configurations."""
        return ["providerName"]
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """Build PaginatedRequest for tenant in-app configurations."""
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

    async def getConfigurationByTenantId(self, tenantId: UUID) -> TenantInAppConfiguration:
        """Retrieve in-app configuration for a given tenant.
        
        Args:
            tenantId: Tenant identifier

        Returns:
            TenantInAppConfiguration object if found, None otherwise
        """
        async with self.uow:
            config = await self.uow.tenantInAppConfigurations.find(lambda x: x.tenantId == tenantId)
            return config
    
    
        
    # Keep old method for backward compatibility
    async def getAllConfigurationsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[TenantInAppConfigurationResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        return await self.get(req)
    
    async def deleteConfiguration(self, configId: UUID) -> None:
        """Delete an existing in-app configuration (deprecated - use delete() instead)."""
       
        try:
            async with self.uow:
                config = await self.uow.tenantInAppConfigurations.getById(configId)
                if config:
                    cache_key = f"tenant_config:in_app:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    await self.uow.tenantInAppConfigurations.delete(configId)
                    await self.uow.commit()
                else:
                    raise EntityNotFoundError(
                        TenantInAppConfiguration.__name__,
                        str(configId)
                    )
        except Exception as e:
            raise ApplicationException(
                f"Error deleting in-app configuration: {e}",
                code="ERROR_DELETING_IN_APP_CONFIGURATION",
                details={"configId": configId}
            )
        finally:
            if config:
                cache_key = f"tenant_config:in_app:{config.tenantId}"
                await self.redis.delete(cache_key)
                return config
    
    
    async def updateConfiguration(self, config: TenantInAppConfiguration) -> TenantInAppConfiguration:
        """Update an existing in-app configuration (deprecated - use update() instead)."""
        try:
            async with self.uow:
                updated_config = await self.uow.tenantInAppConfigurations.update(config)
                await self.uow.commit()
                cache_key = f"tenant_config:in_app:{config.tenantId}"
                await self.redis.delete(cache_key)
                return updated_config
        except Exception as e:
            raise ApplicationException(
                f"Error updating in-app configuration: {e}",
                code="ERROR_UPDATING_IN_APP_CONFIGURATION",
                details={"configId": config.id}
            )
        finally:
            if config:
                cache_key = f"tenant_config:in_app:{config.tenantId}"
                await self.redis.delete(cache_key)
                return config
    

    async def partialUpdate(self, configId: UUID, updates: Dict[str, Any]) -> TenantInAppConfiguration:
        """Partial update of an existing in-app configuration (deprecated - use partialUpdate() instead)."""
        try:
            async with self.uow:
                config = await self.uow.tenantInAppConfigurations.getById(configId)
                if config:
                    cache_key = f"tenant_config:in_app:{config.tenantId}"
                    await self.redis.delete(cache_key)
                    await self.uow.tenantInAppConfigurations.partialUpdate(configId, updates)
                    await self.uow.commit()
                    return config
        except Exception as e:
            raise ApplicationException(
                f"Error partial updating in-app configuration: {e}",
                code="ERROR_PARTIAL_UPDATING_IN_APP_CONFIGURATION",
                details={"configId": configId}
            )
        finally:
            if config:
                cache_key = f"tenant_config:in_app:{config.tenantId}"
                await self.redis.delete(cache_key)
                return config
    
    async def createConfiguration(self, config: TenantInAppConfiguration) -> TenantInAppConfiguration:
        """Create a new in-app configuration (deprecated - use create() instead)."""
        try:
            async with self.uow:
                created_config = await self.uow.tenantInAppConfigurations.create(config)
                await self.uow.commit()
                cache_key = f"tenant_config:in_app:{config.tenantId}"
                await self.redis.set(cache_key, created_config.__dict__, expire=60*60*24)
                return created_config
        except Exception as e:
            raise ApplicationException(
                f"Error creating in-app configuration: {e}",
                code="ERROR_CREATING_IN_APP_CONFIGURATION",
                details={"config": config}
            )
        finally:
            if config:
                cache_key = f"tenant_config:in_app:{config.tenantId}"
                await self.redis.set(cache_key, config.__dict__, expire=60*60*24)
                return config

