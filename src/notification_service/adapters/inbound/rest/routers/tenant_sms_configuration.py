from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, RelatedFilter
from notification_service.application.services.tenant_sms_configuration_service import TenantSMSConfigurationService
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.adapters.inbound.dto.tenant_sms_confuguration_request_dto import (
    TenantSMSConfigurationRequestDto,
    TenantSMSConfigurationResponseDTO,
    TenantSMSConfigurationFilterDTO
)
from notification_service.adapters.inbound.rest.routers.base_crud_router import BaseCRUDRouter
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ApplicationException, ValidationError
from qena_shared_lib.http import api_controller, get, post, put, patch, delete
from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List

@api_controller(prefix="/tenant-sms-configurations", tags=["Tenant SMS Configurations"])
class TenantSMSConfigurationController(BaseCRUDRouter[TenantSMSConfiguration, TenantSMSConfigurationFilterDTO, TenantSMSConfigurationResponseDTO, TenantSMSConfigurationService, TenantSMSConfigurationRequestDto, TenantSMSConfigurationRequestDto]):
    
    def __init__(self, tenantSmsConfigurationService: TenantSMSConfigurationService = Depends()):
        super().__init__(
            service=tenantSmsConfigurationService,
            prefix="/tenant-sms-configurations",
            tags=["Tenant SMS Configurations"],
            request_dto_class=TenantSMSConfigurationFilterDTO,
            response_dto_class=TenantSMSConfigurationResponseDTO,
            entity_class=TenantSMSConfiguration,
            create_dto_class=TenantSMSConfigurationRequestDto,
            update_dto_class=TenantSMSConfigurationRequestDto
        )
        self.tenantSmsConfigurationService = tenantSmsConfigurationService
    
    def _extract_custom_filters(self, params: TenantSMSConfigurationFilterDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        

        return filters
    
    def _build_paginated_request(self, params: TenantSMSConfigurationFilterDTO) -> PaginatedRequest:
        """
        Build PaginatedRequest with searchFields, relatedFilters, and filters.
        Override this method to provide entity-specific search fields and related filters.
        """
        # Build root filters (including custom filters)
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            try:
                from uuid import UUID
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
        custom_filters = self.service._extract_custom_filters(params)
        root_filters.update(custom_filters)
        
        # Build related filters
        related_filters = self.service._build_related_filters(params)
        
        # Define search fields
        search_fields = ["providerName"]
        
        # Build and return PaginatedRequest
        paginated_request = PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=search_fields,
            filters=root_filters,
            relatedFilters=related_filters
        )
        return paginated_request
    
    @get("/get", response_model=PaginatedResponseDTO[TenantSMSConfigurationResponseDTO])
    async def get(self, params: TenantSMSConfigurationFilterDTO = Depends()) -> PaginatedResponseDTO[TenantSMSConfigurationResponseDTO]:
        """Get tenant SMS configurations by filters."""
        try:
            paginated_request = self._build_paginated_request(params)
            result = await self.service.get(paginated_request)
            return result
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @post("/create", response_model=TenantSMSConfigurationResponseDTO)
    async def create(self, request_dto: TenantSMSConfigurationRequestDto) -> TenantSMSConfigurationResponseDTO:
        """
        Create a new tenant SMS configuration.
        POST /tenant-sms-configurations/create
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
            if hasattr(TenantSMSConfigurationResponseDTO, 'fromEntityWithRelations'):
                return TenantSMSConfigurationResponseDTO.fromEntityWithRelations(created_entity)
            else:
                return created_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @put("/{id}", response_model=TenantSMSConfigurationResponseDTO)
    async def update(self, id: UUID, request_dto: TenantSMSConfigurationRequestDto) -> TenantSMSConfigurationResponseDTO:
        """
        Full update of a tenant SMS configuration.
        PUT /tenant-sms-configurations/{id}
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
            if hasattr(TenantSMSConfigurationResponseDTO, 'fromEntityWithRelations'):
                return TenantSMSConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @patch("/{id}", response_model=TenantSMSConfigurationResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any]) -> TenantSMSConfigurationResponseDTO:
        """
        Partial update of a tenant SMS configuration.
        PATCH /tenant-sms-configurations/{id}
        """
        try:
            # Call service
            updated_entity = await self.service.partial_update(id, updates)
            
            # Convert to response DTO
            if hasattr(TenantSMSConfigurationResponseDTO, 'fromEntityWithRelations'):
                return TenantSMSConfigurationResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete a tenant SMS configuration.
        DELETE /tenant-sms-configurations/{id}
        """
        try:
            await self.service.delete(id)
            return {"message": "Tenant SMS configuration deleted successfully"}
        except ApplicationException as e:
            raise self._handle_error(e)
    
    