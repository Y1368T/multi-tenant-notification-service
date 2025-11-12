from typing import Generic, TypeVar, Type, Dict, Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from qena_shared_lib.http import ControllerBase, get, post, put, patch, delete

from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequestDTO,
    PaginatedRequest,
    RelatedFilter,
    FilterOp,
    SortDirection
)
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import (
    ApplicationException,
    EntityNotFoundError,
    ValidationError,
    ConflictError
)

TEntity = TypeVar('TEntity')
TRequestDTO = TypeVar('TRequestDTO', bound=PaginatedRequestDTO)
TResponseDTO = TypeVar('TResponseDTO')
TService = TypeVar('TService')


class BaseCRUDRouter(ControllerBase, Generic[TEntity, TRequestDTO, TResponseDTO, TService]):
    """
    Base CRUD router providing standard REST endpoints.
    Entity routers should inherit from this and configure it.
    """
    
    def __init__(
        self,
        service: TService,
        prefix: str,
        tags: list[str],
        request_dto_class: Type[TRequestDTO],
        response_dto_class: Type[TResponseDTO],
        entity_class: Type[TEntity],
        create_dto_class: Optional[Type] = None
    ):
        """
        Initialize base CRUD router.
        
        Args:
            service: Service instance
            prefix: URL prefix (e.g., "/tenants")
            tags: OpenAPI tags
            request_dto_class: Request DTO class for GET (filter DTO)
            response_dto_class: Response DTO class
            entity_class: Entity class
            create_dto_class: Optional DTO class for POST/PUT (if different from request_dto_class)
        """
        self.service = service
        self.prefix = prefix
        self.tags = tags
        self.request_dto_class = request_dto_class
        self.create_dto_class = create_dto_class or request_dto_class
        self.response_dto_class = response_dto_class
        self.entity_class = entity_class
    
    def _extract_custom_filters(self, params: Any) -> Dict[str, Any]:
        """
        Extract custom filters from request DTO.
        Override in entity routers to extract entity-specific filters.
        
        Args:
            params: Request DTO
            
        Returns:
            Dictionary of custom filters
        """
        return {}
    
    def _handle_error(self, error: Exception) -> HTTPException:
        """
        Handle service exceptions and map to HTTP status codes.
        
        Args:
            error: Exception from service
            
        Returns:
            HTTPException with appropriate status code
        """
        if isinstance(error, EntityNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error)
            )
        elif isinstance(error, ValidationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error)
            )
        elif isinstance(error, ConflictError):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error)
            )
        elif isinstance(error, ApplicationException):
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(error)
            )
        else:
            # Re-raise unknown exceptions
            raise error
    
    @post("/create",response_model=TResponseDTO)
    async def create(self, request_dto: Any)->TResponseDTO:
        """
        Create a new entity.
        POST /entity
        """
        try:
            # Convert DTO to entity (assuming DTO has toEntity method)
            if hasattr(request_dto, 'toEntity'):
                entity = request_dto.toEntity()
            else:
                raise ValidationError("Request DTO must have toEntity() method")
            
            # Call service
            created_entity = await self.service.create(entity)
            
            # Convert entity to response DTO
            if hasattr(self.response_dto_class, 'fromEntityWithRelations'):
                return self.response_dto_class.fromEntityWithRelations(created_entity)
            else:
                return created_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @get("/get", response_model=PaginatedResponseDTO[TResponseDTO])
    async def get(self, params: PaginatedRequestDTO = Depends())->PaginatedResponseDTO[TResponseDTO]:
        """
        Unified get endpoint supporting single entity (by id) or filtered list.
        GET /entity?id={uuid}  → single entity (paginated with 1 item)
        GET /entity?status=active  → filtered list (paginated)
        
        Note: Child classes should override this method to build PaginatedRequest with
        searchFields, relatedFilters, and filters.
        """
        try:
            # Build PaginatedRequest - child classes should override this method
            # to provide searchFields, relatedFilters, and filters
            paginated_request = self._build_paginated_request(params)
            
            # Call service with PaginatedRequest
            result = await self.service.get(paginated_request)
            return result
        except ApplicationException as e:
            raise self._handle_error(e)
    
    def _build_paginated_request(self, params: PaginatedRequestDTO) -> PaginatedRequest:
        """
        Build PaginatedRequest from PaginatedRequestDTO.
        Override this method in child classes to provide:
        - searchFields: List of fields to search
        - relatedFilters: List of RelatedFilter objects
        - filters: Dictionary of root filters (including custom filters)
        
        Args:
            params: PaginatedRequestDTO from query parameters
            
        Returns:
            PaginatedRequest object with all filters, search fields, and related filters
        """
        # Build root filters
        root_filters = {}
        if hasattr(params, 'id') and params.id:
            # Convert string UUID to UUID if needed
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
        
        # Extract custom filters (override in child classes)
        custom_filters = self._extract_custom_filters(params)
        root_filters.update(custom_filters)
        
        # Build PaginatedRequest with default values
        # Child classes should override this method to provide searchFields and relatedFilters
        return PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=None,  # Override in child classes
            filters=root_filters,
            relatedFilters=[]  # Override in child classes
        )
    
    @put("/{id}", response_model=TResponseDTO)
    async def update(self, id: UUID, request_dto: Any)->TResponseDTO:
        """
        Full update of an entity.
        PUT /entity/{id}
        """
        try:
            # Convert DTO to entity
            if hasattr(request_dto, 'toEntity'):
                entity = request_dto.toEntity()
                # Ensure entity has the correct ID
                entity.id = id
            else:
                raise ValidationError("Request DTO must have toEntity() method")
            
            # Call service
            updated_entity = await self.service.update(entity)
            
            # Convert to response DTO
            if hasattr(self.response_dto_class, 'fromEntityWithRelations'):
                return self.response_dto_class.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @patch("/{id}", response_model=TResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any])->TResponseDTO:
        """
        Partial update of an entity.
        PATCH /entity/{id}
        """
        try:
            # Call service
            updated_entity = await self.service.partial_update(id, updates)
            
            # Convert to response DTO
            if hasattr(self.response_dto_class, 'fromEntityWithRelations'):
                return self.response_dto_class.fromEntityWithRelations(updated_entity)
            else:
                return updated_entity
        except ApplicationException as e:
            raise self._handle_error(e)
    
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID)->Dict[str, str]:
        """
        Delete an entity.
        DELETE /entity/{id}
        """
        try:
            await self.service.delete(id)
            return {"message": f"{self.entity_class.__name__} deleted successfully"}
        except ApplicationException as e:
            raise self._handle_error(e)

