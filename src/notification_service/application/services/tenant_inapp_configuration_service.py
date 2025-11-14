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


class TenantInAppConfigurationService(BaseService[TenantInAppConfiguration, TenantInAppConfigurationResponseDTO]):

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow, TenantInAppConfiguration, TenantInAppConfigurationResponseDTO)
        self.uow = uow
    
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

