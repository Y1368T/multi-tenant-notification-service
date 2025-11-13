from abc import ABC, abstractmethod
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
from pydantic import BaseModel
TEntity = TypeVar('TEntity')
TRequestDTO = TypeVar('TRequestDTO', bound=PaginatedRequestDTO)
TResponseDTO = TypeVar('TResponseDTO')
TService = TypeVar('TService')
TCreateDTO = TypeVar('TCreateDTO', bound=BaseModel)

TUpdateDTO = TypeVar('TUpdateDTO', bound=BaseModel)

class BaseCRUDRouter(ControllerBase, ABC, Generic[TEntity, TRequestDTO, TResponseDTO, TService, TCreateDTO, TUpdateDTO]):
    """
    Abstract base CRUD router providing standard REST endpoints.
    Entity routers must inherit from this and implement abstract methods.
    """
    
    def __init__(
        self,
        service: TService,
        prefix: str,
        tags: list[str],
        request_dto_class: Type[TRequestDTO],
        response_dto_class: Type[TResponseDTO],
        entity_class: Type[TEntity],
        create_dto_class: Optional[Type[TCreateDTO]] = None,
        update_dto_class: Optional[Type[TUpdateDTO]] = None
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
    
    @abstractmethod
    def _extract_custom_filters(self, params: TRequestDTO) -> Dict[str, Any]:
        """
        Extract custom filters from request DTO.
        Must be implemented by entity routers to extract entity-specific filters.
        
        Args:
            params: Request DTO (filter DTO)
            
        Returns:
            Dictionary of custom filters
        """
        pass
    
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
    
    @abstractmethod
    def _build_paginated_request(self, params: TRequestDTO) -> PaginatedRequest:
        """
        Build PaginatedRequest from PaginatedRequestDTO.
        Must be implemented by entity routers to provide:
        - searchFields: List of fields to search
        - relatedFilters: List of RelatedFilter objects
        - filters: Dictionary of root filters (including custom filters)
        
        Args:
            params: PaginatedRequestDTO from query parameters
            
        Returns:
            PaginatedRequest object with all filters, search fields, and related filters
        """
        pass
    
    @abstractmethod
    @post("/create", response_model=TResponseDTO)
    async def create(self, request_dto: TCreateDTO) -> TResponseDTO:
        """
        Create a new entity.
        POST /entity/create
        
        Must be implemented by entity routers with concrete DTO types for proper Swagger documentation.
        """
        pass
    
    @abstractmethod
    @get("/get", response_model=PaginatedResponseDTO[TResponseDTO])
    async def get(self, params: TRequestDTO = Depends()) -> PaginatedResponseDTO[TResponseDTO]:
        """
        Unified get endpoint supporting single entity (by id) or filtered list.
        GET /entity/get?id={uuid}  → single entity (paginated with 1 item)
        GET /entity/get?status=active  → filtered list (paginated)
        
        Must be implemented by entity routers with concrete DTO types for proper Swagger documentation.
        """
        pass
    
    @abstractmethod
    @put("/{id}", response_model=TResponseDTO)
    async def update(self, id: UUID, request_dto: TUpdateDTO) -> TResponseDTO:
        """
        Full update of an entity.
        PUT /entity/{id}
        
        Must be implemented by entity routers with concrete DTO types for proper Swagger documentation.
        """
        pass
    
    @abstractmethod
    @patch("/{id}", response_model=TResponseDTO)
    async def partial_update(self, id: UUID, updates: Dict[str, Any]) -> TResponseDTO:
        """
        Partial update of an entity.
        PATCH /entity/{id}
        
        Must be implemented by entity routers.
        """
        pass
    
    @abstractmethod
    @delete("/{id}", response_model=Dict[str, str])
    async def delete(self, id: UUID) -> Dict[str, str]:
        """
        Delete an entity.
        DELETE /entity/{id}
        
        Must be implemented by entity routers.
        """
        pass

