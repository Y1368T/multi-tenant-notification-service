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
    async def getById(self, entity_id: UUID) -> Optional[T]:
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
            templates = await repo.find(lambda t: t.isActive and t.tenantId == tenantId)
        """
        pass
    
    @abstractmethod
    async def firstOrDefault(
        self,
        predicate: Optional[Callable[[T], bool]] = None
    ) -> Optional[T]:
        """
        Get first entity matching predicate or None (EF FirstOrDefault).
        
        Args:
            predicate: Optional lambda expression
            
        Example:
            template = await repo.firstOrDefault(lambda t: t.templateName == "welcome")
        """
        pass
    
    @abstractmethod
    async def singleOrDefault(
        self,
        predicate: Callable[[T], bool]
    ) -> Optional[T]:
        """
        Get single entity matching predicate, raises if multiple (EF SingleOrDefault).
        
        Args:
            predicate: Lambda expression
            
        Example:
            template = await repo.singleOrDefault(lambda t: t.id == template_id)
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
            exists = await repo.any(lambda t: t.templateName == "welcome")
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
            total = await repo.count(lambda t: t.isActive)
        """
        pass
    
    @abstractmethod
    async def orderBy(
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
            templates = await repo.orderBy(
                lambda t: t.createdAt,
                descending=True,
                predicate=lambda t: t.isActive
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
                lambda t: t.templateName,
                predicate=lambda t: t.isActive
            )
        """
        pass
    
    @abstractmethod
    async def listPaginated(
        self,
        page: int,
        pageSize: int,
        filters: Optional[Dict[str, Any]] = None,
        loaderOptions: Optional[List[Any]] = None,
        orderBy: Optional[Any] = None
    ):
        """
        List entities with pagination and optional filtering.
        
        Args:
            page: Page number (1-indexed)
            pageSize: Number of items per page
            filters: Optional dictionary of field: value filters
            loaderOptions: Optional SQLAlchemy loader options (e.g., joinedload)
            orderBy: Optional SQLAlchemy orderBy clause
            
        Returns:
            PaginatedResult with items and metadata
            
        Example:
            result = await repo.listPaginated(
                page=1,
                pageSize=10,
                filters={"isActive": True},
                orderBy=Model.createdAt.desc()
            )
        """
        pass
    
    @abstractmethod
    async def findPaginated(
        self,
        predicate: Callable[[T], bool],
        page: int,
        pageSize: int,
        loaderOptions: Optional[List[Any]] = None
    ):
        """
        Find entities matching predicate with pagination.
        
        Args:
            predicate: Lambda expression to filter entities
            page: Page number (1-indexed)
            pageSize: Number of items per page
            loaderOptions: Optional SQLAlchemy loader options
            
        Returns:
            PaginatedResult with items and metadata
            
        Example:
            result = await repo.findPaginated(
                lambda t: t.isActive and t.tenantId == tenantId,
                page=1,
                pageSize=20
            )
        """
        pass
    
    @abstractmethod
    async def listByRelatedEqual(
        self,
        relatedModel: Any,
        relationshipName: str,
        relatedField: str,
        value: Any,
        page: Optional[int] = None,
        pageSize: Optional[int] = None,
        eager: bool = True
    ) -> Union[List[T], Any]:
        """
        List entities by filtering on related model field.
        
        Args:
            relatedModel: Related SQLAlchemy model class
            relationshipName: Relationship attribute name on primary model
            relatedField: Column name on related model to filter
            value: Value to match
            page: Optional page number for pagination
            pageSize: Optional page size for pagination
            eager: Whether to eager load the relationship
            
        Returns:
            List of entities or PaginatedResult if pagination parameters provided
            
        Example:
            # Get all notifications for a tenant through template relationship
            result = await smsNotificationsRepo.listByRelatedEqual(
                relatedModel=SmsTemplateModel,
                relationshipName="template",
                relatedField="tenantId",
                value=tenantId,
                page=1,
                pageSize=10,
                eager=True
            )
        """
        pass
    
    @abstractmethod
    async def listAdvancedPaginated(
        self,
        page: int,
        pageSize: int,
        *,
        rootFilters: Optional[Dict[str, Any]] = None,
        relatedFilters: Optional[List[Any]] = None,
        includes: Optional[List[str]] = None,
        sortBy: Optional[str] = None,
        sortDirection: str = "desc",
        searchText: Optional[str] = None,
        searchFields: Optional[List[str]] = None
    ):
        """
        Fully generic, SQL-only deep query with eager loading, filters, sorting and search.
        Returns a PaginatedResult of entities.
        
        Args:
            page: Page number (1-indexed)
            pageSize: Page size (max is enforced by caller)
            rootFilters: Dict of root field equals filters
            relatedFilters: List of (relationshipPath, field, op, value)
            includes: Relationship paths for eager loading
            sortBy: Field or dotted path (e.g., "template.tenant.name")
            sortDirection: "asc" or "desc"
            searchText: Text to search using ILIKE
            searchFields: List of fields or dotted paths to OR-match against
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
                .order_by_descending(lambda x: x.createdAt)
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
            query = repo.where(lambda x: x.isActive)
            results = await query.to_list()
        """
        pass
    
    