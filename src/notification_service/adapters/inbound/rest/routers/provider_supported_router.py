from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from qena_shared_lib.http import ControllerBase, api_controller, get, post, delete, put, patch
from notification_service.application.services.provider_service import ProviderService
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from notification_service.domain.entities.providers_supported import Provider
from notification_service.adapters.inbound.dto.provider_supported_dto import (
    ProviderSupportedDTO,
    ProviderResponseDTO,
    ProviderFilterDTO,
    TestRequestDto
)
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, RelatedFilter
from notification_service.adapters.inbound.rest.routers.base_crud_router import BaseCRUDRouter
from notification_service.shared.exceptions.application_exceptions import ApplicationException, ValidationError
from uuid import UUID
from typing import Dict, Any, Optional, List
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)

@api_controller(prefix="/provider-supported", tags=["Provider Supported"])
class ProviderSupportedController(BaseCRUDRouter[Provider, ProviderFilterDTO, ProviderResponseDTO, ProviderService, ProviderSupportedDTO, ProviderSupportedDTO]):
    
    def __init__(self, provider_service: ProviderService = Depends()):
        super().__init__(
            service=provider_service,
            prefix="/provider-supported",
            tags=["Provider Supported"],
            request_dto_class=ProviderFilterDTO,
            response_dto_class=ProviderResponseDTO,
            entity_class=Provider,
            create_dto_class=ProviderSupportedDTO,
            update_dto_class=ProviderSupportedDTO
        )
        self.provider_service = provider_service
    
    def _extract_custom_filters(self, params: ProviderFilterDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'channel') and params.channel:
            filters["channel"] = params.channel
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters

    def _build_paginated_request(self, params: ProviderFilterDTO) -> PaginatedRequest:
        """
        Build PaginatedRequest with searchFields, relatedFilters, and filters.
        Override this method to provide entity-specific search fields and related filters.
        """
        # Build root filters (including custom filters)
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                from uuid import UUID
                if isinstance(params.id, str):
                    root_filters['id'] = UUID(params.id)
                else:
                    root_filters['id'] = params.id
            except (ValueError, AttributeError):
                root_filters['id'] = params.id
        
        # Extract custom filters
        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)
        
        # Define search fields for providers
        search_fields = ["providerName", "displayName", "channel"]
        
        # Define related filters (providers don't have related filters by default)
        related_filters: List[RelatedFilter] = []
        
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
    
        
    @get("/get", response_model=PaginatedResponseDTO[ProviderResponseDTO])
    async def get(self, params: ProviderFilterDTO = Depends()) -> PaginatedResponseDTO[ProviderResponseDTO]:
        """Get providers by filters."""
        try:
            # Build PaginatedRequest with all filters, search fields, and related filters
            paginated_request = self._build_paginated_request(params)
            
            # Call service with PaginatedRequest
            result = await self.service.get(paginated_request)
            return result
        except ApplicationException as e:
            raise self._handle_error(e)
    
    
    @post("/create", response_model=ProviderResponseDTO)
    async def create(self, request_dto: ProviderSupportedDTO) -> ProviderResponseDTO:
        """
        Create a new provider.
        POST /provider-supported/create
        """
        try:
            # Convert DTO to entity
            if hasattr(request_dto, 'toEntity'):
                entity = request_dto.toEntity()
            else:
                raise ValidationError("Request DTO must have toEntity() method")
            
            # Call service
            created_entity = await self.service.create(entity)
            
            # Convert entity to response DTO
            if hasattr(ProviderResponseDTO, 'fromEntityWithRelations'):
                return ProviderResponseDTO.fromEntityWithRelations(created_entity)
            else:
                return created_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @put("/{id}", response_model=ProviderResponseDTO)
    async def update(self, id: UUID, request_dto: ProviderSupportedDTO) -> ProviderResponseDTO:
        """
        Full update of a provider.
        PUT /provider-supported/{id}
        """
        try:
            # Convert DTO to entity
            if hasattr(request_dto, 'toEntity'):
                entity = request_dto.toEntity()
                entity.id = id
            else:
                raise ValidationError("Request DTO must have toEntity() method")
            
            # Call service
            updated_entity = await self.service.update(entity)
            
            # Convert to response DTO
            if hasattr(ProviderResponseDTO, 'fromEntityWithRelations'):
                return ProviderResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @patch("/{id}", response_model=ProviderResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any]) -> ProviderResponseDTO:
        """
        Partial update of a provider.
        PATCH /provider-supported/{id}
        """
        try:
            # Call service
            updated_entity = await self.service.partial_update(id, updates)
            
            # Convert to response DTO
            if hasattr(ProviderResponseDTO, 'fromEntityWithRelations'):
                return ProviderResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete a provider.
        DELETE /provider-supported/{id}
        """
        try:
            await self.service.delete(id)
            return {"message": "Provider deleted successfully"}
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @post("/test", response_model=ProviderTestResponse)
    async def test_provider(self, dto: TestRequestDto) -> ProviderTestResponse:
        """Test a provider (custom endpoint)."""
        return await self.provider_service.test_provider(dto)
    