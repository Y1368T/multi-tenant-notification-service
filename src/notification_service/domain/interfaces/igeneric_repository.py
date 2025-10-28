"""
Generic repository interface.
Base interface for all repository implementations.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from uuid import UUID


T = TypeVar('T')


class IGenericRepository(ABC, Generic[T]):
    """
    Generic repository interface following Repository Pattern.
    Provides CRUD operations for domain entities.
    """
    
    @abstractmethod
    async def add(self, entity: T) -> T:
        """
        Add new entity to repository.
        
        Args:
            entity: Domain entity to persist
            
        Returns:
            Persisted entity with generated ID
        """
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """
        Update existing entity.
        
        Args:
            entity: Domain entity with updated values
            
        Returns:
            Updated entity
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> None:
        """
        Delete entity by ID.
        
        Args:
            entity_id: Entity identifier
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Retrieve entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Domain entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """
        List entities with optional filtering and pagination.
        
        Args:
            filters: Filter conditions (e.g., {"status": "active"})
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of domain entities
        """
        pass
