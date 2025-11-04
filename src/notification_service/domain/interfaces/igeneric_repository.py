from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any, Callable
from uuid import UUID


T = TypeVar('T')
M = TypeVar('M')


class IGenericRepository(ABC, Generic[T]):
    """
    Generic repository interface following Repository Pattern.
    Provides CRUD operations for domain entities.
    """
    
    @abstractmethod
    async def add(self, entity: T) -> T:
        """Add new entity to repository."""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> None:
        """Delete entity by ID."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Retrieve entity by ID."""
        pass
    
    @abstractmethod
    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """List entities with optional filtering and pagination."""
        pass
    
    # Entity Framework-style Expression methods
    
    @abstractmethod
    async def find(
        self,
        predicate: Callable[[T], bool]
    ) -> List[T]:
        """
        Find entities matching predicate (Entity Framework Find/Where).
        
        Args:
            predicate: Lambda expression to filter entities
            
        Example:
            templates = await repo.find(lambda t: t.is_active and t.tenant_id == tenant_id)
        """
        pass
    
    @abstractmethod
    async def first_or_default(
        self,
        predicate: Optional[Callable[[T], bool]] = None
    ) -> Optional[T]:
        """
        Get first entity matching predicate or None (EF FirstOrDefault).
        
        Args:
            predicate: Optional lambda expression
            
        Example:
            template = await repo.first_or_default(lambda t: t.template_name == "welcome")
        """
        pass
    
    @abstractmethod
    async def single_or_default(
        self,
        predicate: Callable[[T], bool]
    ) -> Optional[T]:
        """
        Get single entity matching predicate, raises if multiple (EF SingleOrDefault).
        
        Args:
            predicate: Lambda expression
            
        Example:
            template = await repo.single_or_default(lambda t: t.id == template_id)
        """
        pass
    
    @abstractmethod
    async def any(
        self,
        predicate: Optional[Callable[[T], bool]] = None
    ) -> bool:
        """
        Check if any entity matches predicate (EF Any).
        
        Example:
            exists = await repo.any(lambda t: t.template_name == "welcome")
        """
        pass
    
    @abstractmethod
    async def count(
        self,
        predicate: Optional[Callable[[T], bool]] = None
    ) -> int:
        """
        Count entities matching predicate (EF Count).
        
        Example:
            total = await repo.count(lambda t: t.is_active)
        """
        pass
    
    @abstractmethod
    async def order_by(
        self,
        key_selector: Callable[[T], Any],
        descending: bool = False,
        predicate: Optional[Callable[[T], bool]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """
        Order entities by key selector (EF OrderBy/OrderByDescending).
        
        Args:
            key_selector: Lambda to extract sort key
            descending: Sort descending if True
            predicate: Optional filter
            
        Example:
            templates = await repo.order_by(
                lambda t: t.created_at,
                descending=True,
                predicate=lambda t: t.is_active
            )
        """
        pass
    
    @abstractmethod
    async def select(
        self,
        selector: Callable[[T], Any],
        predicate: Optional[Callable[[T], bool]] = None
    ) -> List[Any]:
        """
        Project entities using selector (EF Select).
        
        Args:
            selector: Lambda to transform entity
            predicate: Optional filter
            
        Example:
            names = await repo.select(
                lambda t: t.template_name,
                predicate=lambda t: t.is_active
            )
        """
        pass