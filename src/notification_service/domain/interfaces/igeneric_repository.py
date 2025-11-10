from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any, Callable, Union
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
    
    @abstractmethod
    async def list_paginated(
        self,
        page: int,
        page_size: int,
        filters: Optional[Dict[str, Any]] = None,
        loader_options: Optional[List[Any]] = None,
        order_by: Optional[Any] = None
    ):
        """
        List entities with pagination and optional filtering.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Optional dictionary of field: value filters
            loader_options: Optional SQLAlchemy loader options (e.g., joinedload)
            order_by: Optional SQLAlchemy order_by clause
            
        Returns:
            PaginatedResult with items and metadata
            
        Example:
            result = await repo.list_paginated(
                page=1,
                page_size=10,
                filters={"is_active": True},
                order_by=Model.created_at.desc()
            )
        """
        pass
    
    @abstractmethod
    async def find_paginated(
        self,
        predicate: Callable[[T], bool],
        page: int,
        page_size: int,
        loader_options: Optional[List[Any]] = None
    ):
        """
        Find entities matching predicate with pagination.
        
        Args:
            predicate: Lambda expression to filter entities
            page: Page number (1-indexed)
            page_size: Number of items per page
            loader_options: Optional SQLAlchemy loader options
            
        Returns:
            PaginatedResult with items and metadata
            
        Example:
            result = await repo.find_paginated(
                lambda t: t.is_active and t.tenant_id == tenant_id,
                page=1,
                page_size=20
            )
        """
        pass
    
    @abstractmethod
    async def list_by_related_equal(
        self,
        related_model: Any,
        relationship_name: str,
        related_field: str,
        value: Any,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        eager: bool = True
    ) -> Union[List[T], Any]:
        """
        List entities by filtering on related model field.
        
        Args:
            related_model: Related SQLAlchemy model class
            relationship_name: Relationship attribute name on primary model
            related_field: Column name on related model to filter
            value: Value to match
            page: Optional page number for pagination
            page_size: Optional page size for pagination
            eager: Whether to eager load the relationship
            
        Returns:
            List of entities or PaginatedResult if pagination parameters provided
            
        Example:
            # Get all notifications for a tenant through template relationship
            result = await sms_notifications_repo.list_by_related_equal(
                related_model=SmsTemplateModel,
                relationship_name="template",
                related_field="tenant_id",
                value=tenant_id,
                page=1,
                page_size=10,
                eager=True
            )
        """
        pass
    
    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """
        Check if entity exists by ID.
        
        Args:
            entity_id: UUID of the entity
            
        Returns:
            True if entity exists, False otherwise
            
        Example:
            exists = await repo.exists(template_id)
        """
        pass
    
    @abstractmethod
    def query(self):
        """
        Return LINQ-style query builder for fluent querying.
        
        Returns:
            LinqQuery builder instance
            
        Example:
            result = await repo.query()
                .where(lambda x: x.status == "active")
                .order_by_descending(lambda x: x.created_at)
                .to_paginated_list(page=1, page_size=10)
        """
        pass
    
    @abstractmethod
    def where(self, predicate: Callable[[T], bool]):
        """
        Create LINQ-style query with where clause.
        
        Args:
            predicate: Lambda expression to filter entities
            
        Returns:
            LinqQuery builder instance
            
        Example:
            query = repo.where(lambda x: x.is_active)
            results = await query.to_list()
        """
        pass
    
    