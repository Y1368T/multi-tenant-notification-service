from fastapi import Depends
from uuid import UUID
from typing import Dict, Any, List
from notification_service.application.services.tenant_service import TenantService
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adapters.inbound.dto.tenant_request_dto import (
    TenantRequestDTO,
    TenantResponseDTO,
    TenantFilterDTO
)
from notification_service.adapters.inbound.rest.routers.base_crud_router import BaseCRUDRouter
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequestDTO,
    PaginatedRequest,
    RelatedFilter,
    FilterOp
)
from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import ValidationError, ApplicationException
from qena_shared_lib.http import api_controller, get, post, put, patch, delete

@api_controller(prefix="/tenants", tags=["Tenants"])
class TenantController(BaseCRUDRouter[Tenant, TenantFilterDTO, TenantResponseDTO, TenantService, TenantRequestDTO, TenantRequestDTO]):
    """Controller for tenant-related endpoints."""
    
    def __init__(self, tenantService: TenantService = Depends()):
        super().__init__(
            service=tenantService,
            prefix="/tenants",
            tags=["Tenants"],
            request_dto_class=TenantFilterDTO,
            response_dto_class=TenantResponseDTO,
            entity_class=Tenant,
            create_dto_class=TenantRequestDTO,
            update_dto_class=TenantRequestDTO
        )
    
    def _extract_custom_filters(self, params: TenantFilterDTO) -> Dict[str, Any]:
        """
        Extract custom filters from request DTO.
        Override this method to extract entity-specific filters.
        Always use hasattr() to safely check for custom attributes.
        """
        filters = {}
        # Safely check for status attribute (TenantFilterDTO extends PaginatedRequestDTO)
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        return filters
    
    def _build_paginated_request(self, params: TenantFilterDTO) -> PaginatedRequest:
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
        
        if hasattr(params, 'tenantId') and params.tenantId:
            root_filters['tenantId'] = params.tenantId
        
        # Extract custom filters
        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)
        
        # Define search fields for tenants
        search_fields = ["name", "prefix"]
        
        # Define related filters (tenants don't have related filters by default)
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
    
    @get("/get", response_model=PaginatedResponseDTO[TenantResponseDTO])
    async def get(self, params: TenantFilterDTO = Depends())->PaginatedResponseDTO[TenantResponseDTO]:
        """
        Get tenants by filters.
        GET /tenants/get?id={uuid}  → single tenant (paginated with 1 item)
        GET /tenants/get?status=active&page=1&page_size=20  → filtered list (paginated)
        """
        try:
            # Build PaginatedRequest with all filters, search fields, and related filters
            paginated_request = self._build_paginated_request(params)
            
            # Call service with PaginatedRequest
            result = await self.service.get(paginated_request)
            return result
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @post("/create", response_model=TenantResponseDTO)
    async def create(self, request_dto: TenantRequestDTO) -> TenantResponseDTO:
        """
        Create a new tenant with validation.
        POST /tenants/create
        
        Override this method to add custom validation or business logic.
        """
        try:
            # Validate preferred communication method
            if request_dto.preferedCommunicationMethod not in ["rest", "kafka", "rabbitmq", "grpc"]:
                raise ValidationError("Invalid preferred communication method. Must be one of: rest, kafka, rabbitmq, grpc")
            
            # Convert DTO to entity
            if hasattr(request_dto, 'toEntity'):
                entity = request_dto.toEntity()
            else:
                raise ValidationError("Request DTO must have toEntity() method")
            
            # Call service
            created_entity = await self.service.create(entity)
            
            # Convert entity to response DTO
            if hasattr(TenantResponseDTO, 'fromEntityWithRelations'):
                return TenantResponseDTO.fromEntityWithRelations(created_entity)
            else:
                return created_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @put("/{id}", response_model=TenantResponseDTO)
    async def update(self, id: UUID, request_dto: TenantRequestDTO) -> TenantResponseDTO:
        """
        Full update of a tenant.
        PUT /tenants/{id}
        
        Override this method to add custom validation or business logic.
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
            if hasattr(TenantResponseDTO, 'fromEntityWithRelations'):
                return TenantResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @patch("/{id}", response_model=TenantResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any]) -> TenantResponseDTO:
        """
        Partial update of a tenant.
        PATCH /tenants/{id}
        
        Override this method to add custom validation for partial updates.
        """
        try:
            # Add custom validation for partial updates
            if "preferedCommunicationMethod" in updates:
                if updates["preferedCommunicationMethod"] not in ["rest", "kafka", "rabbitmq", "grpc"]:
                    raise ValidationError("Invalid preferred communication method. Must be one of: rest, kafka, rabbitmq, grpc")
            
            # Call service
            updated_entity = await self.service.partial_update(id, updates)
            
            # Convert to response DTO
            if hasattr(TenantResponseDTO, 'fromEntityWithRelations'):
                return TenantResponseDTO.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete a tenant.
        DELETE /tenants/{id}
        """
        try:
            await self.service.delete(id)
            return {"message": "Tenant deleted successfully"}
        except ApplicationException as e:
            raise self._handle_error(e)