from typing import TypeVar, Generic, Callable, Optional, Any, List, Dict
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.domain.value_objects.paginated_result import PaginatedResult

T = TypeVar('T')
M = TypeVar('M')

class LinqQuery(Generic[T, M]):
    """
    LINQ-style query builder for fluent querying.
    Supports method chaining similar to Entity Framework LINQ.
    """
    
    def __init__(self, model_class: type[M], session: AsyncSession, mapper: Any):
        self._model_class = model_class
        self._session = session
        self._mapper = mapper
        self._stmt = select(model_class)
        self._predicates: List[Callable[[T], bool]] = []
        self._includes: List[Any] = []
        self._order_clauses: List[tuple] = []
        self._selector: Optional[Callable[[T], Any]] = None
        self._distinct = False
        
    def include(self, *paths) -> "LinqQuery[T, M]":
        """
        Eager load related entities (similar to EF Include).
        Supports multiple paths and nested paths using dot notation.
        
        Args:
            *paths: Relationship paths to eager load. Can be:
                   - String paths: "template", "template.tenant"
                   - Lambda expressions: lambda x: x.template
                   
        Returns:
            Self for method chaining
            
        Example:
            query.include("template", "template.tenant", "user")
            query.include(lambda x: x.template).include(lambda x: x.template.tenant)
        """
        for path in paths:
            if callable(path):
                # Lambda expression - extract attribute name
                # This is simplified; real implementation would need expression parsing
                path_str = self._extract_path_from_lambda(path)
            else:
                path_str = path
                
            # Build selectinload chain for nested paths
            if "." in path_str:
                parts = path_str.split(".")
                loader = selectinload(getattr(self._model_class, parts[0]))
                
                current_model = getattr(self._model_class, parts[0]).property.mapper.class_
                for part in parts[1:]:
                    loader = loader.selectinload(getattr(current_model, part))
                    current_model = getattr(current_model, part).property.mapper.class_
                    
                self._includes.append(loader)
            else:
                self._includes.append(selectinload(getattr(self._model_class, path_str)))
                
        return self
    
    def where(self, predicate: Callable[[Any], bool]) -> "LinqQuery[T, M]":
        """
        Filter entities using lambda predicate (similar to EF Where).
        Multiple where clauses are combined with AND.
        
        Args:
            predicate: Lambda expression to filter entities
            
        Returns:
            Self for method chaining
            
        Example:
            query.where(lambda x: x.is_active)
                 .where(lambda x: x.parent1.id == id)
                 .where(lambda x: x.parent2.is_active and x.parent3.id == other_id)
        """
        self._predicates.append(predicate)
        return self
    
    def where_any(self, *predicates: Callable[[Any], bool]) -> "LinqQuery[T, M]":
        """
        Filter entities where ANY predicate matches (OR condition).
        
        Args:
            *predicates: Multiple lambda expressions (OR combined)
            
        Returns:
            Self for method chaining
            
        Example:
            query.where_any(
                lambda x: x.status == "active",
                lambda x: x.status == "pending"
            )
        """
        def combined_predicate(x):
            return any(pred(x) for pred in predicates)
        self._predicates.append(combined_predicate)
        return self
    
    def order_by(self, key_selector: Callable[[Any], Any], column_name: Optional[str] = None) -> "LinqQuery[T, M]":
        """
        Order results ascending (similar to EF OrderBy).
        
        Args:
            key_selector: Lambda to extract sort key
            column_name: Optional column name for SQL ordering
            
        Returns:
            Self for method chaining
            
        Example:
            query.order_by(lambda x: x.created_at, "created_at")
        """
        self._order_clauses.append((key_selector, column_name, False))
        return self
    
    def order_by_descending(self, key_selector: Callable[[Any], Any], column_name: Optional[str] = None) -> "LinqQuery[T, M]":
        """
        Order results descending (similar to EF OrderByDescending).
        
        Args:
            key_selector: Lambda to extract sort key
            column_name: Optional column name for SQL ordering
            
        Returns:
            Self for method chaining
            
        Example:
            query.order_by_descending(lambda x: x.created_at, "created_at")
        """
        self._order_clauses.append((key_selector, column_name, True))
        return self
    
    def then_by(self, key_selector: Callable[[Any], Any], column_name: Optional[str] = None) -> "LinqQuery[T, M]":
        """
        Add secondary ascending sort (similar to EF ThenBy).
        
        Args:
            key_selector: Lambda to extract sort key
            column_name: Optional column name for SQL ordering
            
        Returns:
            Self for method chaining
            
        Example:
            query.order_by(lambda x: x.tenant_id, "tenant_id")
                 .then_by(lambda x: x.created_at, "created_at")
        """
        self._order_clauses.append((key_selector, column_name, False))
        return self
    
    def then_by_descending(self, key_selector: Callable[[Any], Any], column_name: Optional[str] = None) -> "LinqQuery[T, M]":
        """
        Add secondary descending sort (similar to EF ThenByDescending).
        """
        self._order_clauses.append((key_selector, column_name, True))
        return self
    
    def select(self, selector: Callable[[Any], Any]) -> "LinqQuery[T, M]":
        """
        Project entities to new shape (similar to EF Select).
        
        Args:
            selector: Lambda to transform entities
            
        Returns:
            Self for method chaining
            
        Example:
            query.select(lambda x: {"id": x.id, "name": x.template_name})
            query.select(lambda x: x.template_name)
        """
        self._selector = selector
        return self
    
    def distinct(self) -> "LinqQuery[T, M]":
        """
        Get distinct results (similar to EF Distinct).
        
        Returns:
            Self for method chaining
        """
        self._distinct = True
        return self
    
    def skip(self, count: int) -> "LinqQuery[T, M]":
        """
        Skip number of results (similar to EF Skip).
        
        Args:
            count: Number of items to skip
            
        Returns:
            Self for method chaining
        """
        self._stmt = self._stmt.offset(count)
        return self
    
    def take(self, count: int) -> "LinqQuery[T, M]":
        """
        Take number of results (similar to EF Take).
        
        Args:
            count: Maximum number of items to return
            
        Returns:
            Self for method chaining
        """
        self._stmt = self._stmt.limit(count)
        return self
    
    async def to_list(self) -> List[Any]:
        """
        Execute query and return list of results.
        
        Returns:
            List of entities or projected values
            
        Example:
            results = await query.to_list()
        """
        # Apply includes
        for include in self._includes:
            self._stmt = self._stmt.options(include)
        
        # Apply SQL-level ordering if column names provided
        for key_selector, column_name, descending in self._order_clauses:
            if column_name:
                col = getattr(self._model_class, column_name)
                self._stmt = self._stmt.order_by(col.desc() if descending else col.asc())
        
        # Apply distinct
        if self._distinct:
            self._stmt = self._stmt.distinct()
        
        # Execute query
        result = await self._session.execute(self._stmt)
        models = result.unique().scalars().all()
        
        # Map to entities
        entities = [self._mapper.to_entity(m) for m in models]
        
        # Apply in-memory predicates
        for predicate in self._predicates:
            entities = [e for e in entities if predicate(e)]
        
        # Apply in-memory ordering if no column name provided
        for key_selector, column_name, descending in self._order_clauses:
            if not column_name:
                entities = sorted(entities, key=key_selector, reverse=descending)
        
        # Apply selector if provided
        if self._selector:
            entities = [self._selector(e) for e in entities]
        
        return entities
    
    async def to_paginated_list(self, page: int, page_size: int) -> PaginatedResult:
        """
        Execute query and return paginated results.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            PaginatedResult with items and metadata
            
        Example:
            result = await query.to_paginated_list(page=1, page_size=10)
        """
        # Get total count before pagination
        count_stmt = select(func.count()).select_from(self._model_class)
        total_count = (await self._session.execute(count_stmt)).scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        self._stmt = self._stmt.offset(offset).limit(page_size)
        
        # Get items
        items = await self.to_list()
        
        # If predicates were applied, recalculate count
        if self._predicates:
            total_count = len(items) + offset
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    
    async def first_or_default(self) -> Optional[Any]:
        """
        Get first result or None (similar to EF FirstOrDefault).
        
        Returns:
            First entity or None
            
        Example:
            entity = await query.first_or_default()
        """
        self._stmt = self._stmt.limit(1)
        results = await self.to_list()
        return results[0] if results else None
    
    async def single_or_default(self) -> Optional[Any]:
        """
        Get single result or None, raises if multiple (similar to EF SingleOrDefault).
        
        Returns:
            Single entity or None
            
        Raises:
            ValueError: If multiple results found
            
        Example:
            entity = await query.single_or_default()
        """
        results = await self.to_list()
        if len(results) > 1:
            raise ValueError("Sequence contains more than one element")
        return results[0] if results else None
    
    async def any(self) -> bool:
        """
        Check if any results exist (similar to EF Any).
        
        Returns:
            True if any results, False otherwise
            
        Example:
            exists = await query.any()
        """
        self._stmt = self._stmt.limit(1)
        results = await self.to_list()
        return len(results) > 0
    
    async def count(self) -> int:
        """
        Get count of results (similar to EF Count).
        
        Returns:
            Number of matching entities
            
        Example:
            total = await query.count()
        """
        results = await self.to_list()
        return len(results)
    
    def _extract_path_from_lambda(self, func: Callable) -> str:
        """
        Extract attribute path from lambda expression.
        Simplified implementation - real version would need proper AST parsing.
        """
        import inspect
        source = inspect.getsource(func)
        # Extract path from lambda x: x.template.tenant
        # This is a simplified approach
        parts = source.split(":")[-1].strip().split(".")
        return ".".join(parts[1:]) if len(parts) > 1 else parts[0]