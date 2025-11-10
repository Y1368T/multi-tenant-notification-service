"""Query extensions for SQLAlchemy queries."""

from typing import TypeVar, Type, Any
from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.domain.value_objects.paginated_result import PaginatedResult
from notification_service.domain.value_objects.paged_request import PagedRequest, SortDirection

TEntity = TypeVar('TEntity')
TModel = TypeVar('TModel')


class QueryableExtensions:
    """Extension methods for SQLAlchemy queries similar to .NET's Queryable extensions."""
    
    @staticmethod
    def apply_paging(query: Select, page: int, page_size: int) -> Select:
        """Apply pagination to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy select statement
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            Query with pagination applied
            
        Example:
            stmt = select(Model)
            stmt = QueryableExtensions.apply_paging(stmt, page=2, page_size=20)
        """
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size)
    
    @staticmethod
    def apply_sorting(
        query: Select,
        model_class: Type[Any],
        sort_by: str,
        sort_direction: SortDirection = SortDirection.ASC
    ) -> Select:
        """Apply sorting to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy select statement
            model_class: SQLAlchemy model class
            sort_by: Column name to sort by
            sort_direction: Sort direction (ASC or DESC)
            
        Returns:
            Query with sorting applied
            
        Example:
            stmt = select(Model)
            stmt = QueryableExtensions.apply_sorting(
                stmt, Model, "created_at", SortDirection.DESC
            )
        """
        if not hasattr(model_class, sort_by):
            raise ValueError(f"Model {model_class.__name__} has no attribute '{sort_by}'")
        
        column = getattr(model_class, sort_by)
        
        if sort_direction == SortDirection.DESC:
            return query.order_by(column.desc())
        else:
            return query.order_by(column)
    
    @staticmethod
    async def to_paged_response_async(
        query: Select,
        session: AsyncSession,
        model_class: Type[TModel],
        mapper: Type[Any],
        paged_request: PagedRequest
    ) -> PaginatedResult[TEntity]:
        """Execute query and return paginated response.
        
        Args:
            query: SQLAlchemy select statement
            session: SQLAlchemy async session
            model_class: SQLAlchemy model class
            mapper: Mapper to convert model to entity
            paged_request: Pagination request parameters
            
        Returns:
            PaginatedResult with items and metadata
            
        Example:
            stmt = select(Model).where(Model.status == "active")
            result = await QueryableExtensions.to_paged_response_async(
                stmt, session, Model, mapper, PagedRequest(page=1, page_size=20)
            )
        """
        # Count total records
        count_query = query.with_only_columns(func.count()).order_by(None)
        total_count = await session.scalar(count_query)
        
        # Apply sorting if specified
        if paged_request.sort_by:
            query = QueryableExtensions.apply_sorting(
                query,
                model_class,
                paged_request.sort_by,
                paged_request.sort_direction
            )
        
        # Apply pagination
        query = QueryableExtensions.apply_paging(
            query,
            paged_request.page,
            paged_request.page_size
        )
        
        # Execute query
        result = await session.execute(query)
        models = result.scalars().all()
        
        # Convert to entities
        entities = [mapper.to_entity(model) for model in models]
        
        # Calculate metadata
        total_pages = (total_count + paged_request.page_size - 1) // paged_request.page_size
        
        return PaginatedResult(
            items=entities,
            total_count=total_count,
            page=paged_request.page,
            page_size=paged_request.page_size,
            total_pages=total_pages,
            has_next=paged_request.page < total_pages,
            has_previous=paged_request.page > 1
        )
    
    @staticmethod
    def _get_property(obj: Any, property_path: str) -> Any:
        """Get property value using dot notation path.
        
        Args:
            obj: Object to get property from
            property_path: Dot-separated property path (e.g., "template.tenant_id")
            
        Returns:
            Property value
            
        Example:
            value = QueryableExtensions._get_property(notification, "template.tenant_id")
        """
        parts = property_path.split('.')
        current = obj
        
        for part in parts:
            if current is None:
                return None
            current = getattr(current, part, None)
        
        return current
