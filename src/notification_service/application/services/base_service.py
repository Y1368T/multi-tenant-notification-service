from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from uuid import UUID

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequestDTO,
    PaginatedRequest,
    RelatedFilter,
    SortDirection
)
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.shared.exceptions.application_exceptions import EntityNotFoundError, ValidationError

TEntity = TypeVar('TEntity')
TResponseDTO = TypeVar('TResponseDTO')


class BaseService(ABC, Generic[TEntity, TResponseDTO]):
    """
    Base service providing generic CRUD operations.
    Entity services should inherit from this and override methods as needed.
    """
    
    def __init__(self, uow: IUnitOfWork, entity_class: Type[TEntity], response_dto_class: Type[TResponseDTO]):
        """
        Initialize base service.
        
        Args:
            uow: Unit of Work instance
            entity_class: The entity class type
            response_dto_class: The response DTO class type (must have fromEntityWithRelations class method)
        """
        self.uow = uow
        self.entity_class = entity_class
        self.response_dto_class = response_dto_class
    
    @abstractmethod
    def _get_repository(self):
        """
        Get the repository for this entity.
        Must be implemented by entity services.
        
        Returns:
            Repository instance (e.g., self.uow.tenants)
        """
        pass
    
    def _get_includes(self) -> Optional[List[str]]:
        """
        Get relationship paths to eager load.
        Override in entity services to specify which relationships to include.
        
        Returns:
            List of relationship paths (e.g., ["template", "template.tenant"]) or None/empty list
        """
        return []
    
    async def create(self, entity: TEntity) -> TEntity:
        """
        Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity
        """
        async with self.uow:
            repository = self._get_repository()
            created_entity = await repository.add(entity)
            await self.uow.commit()
            return created_entity
    
    async def get(self, paginated_request: PaginatedRequest) -> PaginatedResponseDTO[TResponseDTO]:
        """
        Unified get method supporting single entity (by id) or filtered list.
        Always returns paginated response.
        
        Args:
            paginated_request: PaginatedRequest object with filters, searchFields, and relatedFilters
            
        Returns:
            Paginated response DTO
        """
        async with self.uow:
            repository = self._get_repository()
            
            # Convert related filters to tuples format expected by repository
            related_filters_tuples = [
                (
                    rf.relationshipPath,
                    rf.field,
                    rf.op.value if hasattr(rf.op, 'value') else str(rf.op),
                    rf.value
                )
                for rf in (paginated_request.relatedFilters or [])
            ]
            
            # Get includes for eager loading relationships
            includes = self._get_includes() or []
            
            # Call repository with data from PaginatedRequest
            result = await repository.listAdvancedPaginated(
                page=paginated_request.page,
                pageSize=paginated_request.pageSize,
                rootFilters=paginated_request.filters or {},
                relatedFilters=related_filters_tuples,
                includes=includes,
                sortBy=paginated_request.sortBy or "createdAt",
                sortDirection=paginated_request.sortDirection.value,
                searchText=paginated_request.searchText,
                searchFields=paginated_request.searchFields
            )
            
            # Convert entities to DTOs
            dto_items = [
                self.response_dto_class.fromEntityWithRelations(entity)
                for entity in result.items
            ]
            
            return PaginatedResponseDTO(
                items=dto_items,
                page=result.page,
                pageSize=result.pageSize,
                totalCount=result.totalCount,
                totalPages=result.totalPages,
                hasNext=result.hasNext,
                hasPrevious=result.hasPrevious
            )
    
    async def update(self, entity: TEntity) -> TEntity:
        """
        Full update of an entity.
        Fetches existing entity, merges changes, and saves.
        
        Args:
            entity: Entity with updated values (must have id)
            
        Returns:
            Updated entity
            
        Raises:
            EntityNotFoundError: If entity not found
        """
        async with self.uow:
            repository = self._get_repository()
            
            # Fetch existing entity
            existing = await repository.getById(entity.id)
            if not existing:
                raise EntityNotFoundError(
                    self.entity_class.__name__,
                    str(entity.id)
                )
            
            # Merge changes (update existing entity fields)
            # This is a simple merge - entity services can override for complex logic
            updated_entity = await repository.update(entity)
            await self.uow.commit()
            
            return updated_entity
    
    async def partial_update(self, entity_id: UUID, updates: Dict[str, Any]) -> TEntity:
        """
        Partial update of an entity.
        Fetches existing entity, applies updates, and saves.
        
        Args:
            entity_id: ID of entity to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated entity
            
        Raises:
            EntityNotFoundError: If entity not found
            ValidationError: If validation fails
        """
        async with self.uow:
            repository = self._get_repository()
            
            # Fetch existing entity
            existing = await repository.getById(entity_id)
            if not existing:
                raise EntityNotFoundError(
                    self.entity_class.__name__,
                    str(entity_id)
                )
            
            # Validate and apply updates
            self._validate_partial_update(updates)
            updated_entity = self._apply_partial_updates(existing, updates)
            
            # Save
            saved_entity = await repository.update(updated_entity)
            await self.uow.commit()
            
            return saved_entity
    
    def _validate_partial_update(self, updates: Dict[str, Any]) -> None:
        """
        Validate partial update data.
        Override in entity services for custom validation.
        
        Args:
            updates: Dictionary of updates
            
        Raises:
            ValidationError: If validation fails
        """
        # Base implementation - no validation
        # Entity services can override
        pass
    
    def _apply_partial_updates(self, entity: TEntity, updates: Dict[str, Any]) -> TEntity:
        """
        Apply partial updates to entity.
        Override in entity services for complex update logic.
        
        Args:
            entity: Existing entity
            updates: Dictionary of updates
            
        Returns:
            Entity with updates applied
        """
        # Simple field update
        for key, value in updates.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return entity
    
    async def delete(self, entity_id: UUID) -> None:
        """
        Delete an entity by ID.
        
        Args:
            entity_id: ID of entity to delete
            
        Raises:
            EntityNotFoundError: If entity not found
        """
        async with self.uow:
            repository = self._get_repository()
            
            # Check if entity exists
            existing = await repository.getById(entity_id)
            if not existing:
                raise EntityNotFoundError(
                    self.entity_class.__name__,
                    str(entity_id)
                )
            
            await repository.delete(entity_id)
            await self.uow.commit()

