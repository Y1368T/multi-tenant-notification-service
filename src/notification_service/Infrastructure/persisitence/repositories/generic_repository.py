from sqlalchemy import select, func,delete, update, or_, asc, desc
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, Type, TypeVar, List, Optional, Dict, Any, Callable,Union
from uuid import UUID
from notification_service.domain.interfaces.igeneric_repository import IGenericRepository
import logging
from notification_service.domain.value_objects.paginated_result import PaginatedResult
from notification_service.infrastructure.persisitence.extensions.linq_extensions import LinqQuery

logger = logging.getLogger(__name__)

TEntity = TypeVar('TEntity')
TModel = TypeVar('TModel')
TMapper = TypeVar('TMapper')


class GenericRepository(IGenericRepository[TEntity], Generic[TEntity, TModel]):
    """Base repository implementation with SQLAlchemy."""

    def __init__(self, session: AsyncSession, model_class: Type[TModel], mapper: Type[TMapper]):
        """Initialize repository.
        
        Args:
            session: SQLAlchemy async session
            model_class: The SQLAlchemy model class
        """
        self.session = session
        self.model_class = model_class
        self.mapper = mapper
    
    async def add(self, entity: TEntity) -> TEntity:
        """Add new entity to repository."""
        try:
            model = self.mapper.to_model(entity)
            self.session.add(model)
            await self.session.flush()
            logger.debug(f"Added {self.model_class.__name__} with id {model.id}")
            return self.mapper.to_entity(model)
        except Exception as e:
            logger.error(f"Error adding {self.model_class.__name__}: {e}")
            raise
    
    async def update(self, entity: TEntity) -> TEntity:
        """Update existing entity."""
        try:
            model = self.mapper.to_model(entity)
            merged_model = await self.session.merge(model)
            await self.session.flush()
            logger.debug(f"Updated {self.model_class.__name__} with id {model.id}")
            return self.mapper.to_entity(merged_model)
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__}: {e}")
            raise
    
    async def delete(self, entity_id: UUID) -> None:
        """Delete entity by ID."""
        try:
            query = delete(self.model_class).where(self.model_class.id == entity_id)
            await self.session.execute(query)
            await self.session.flush()
            logger.debug(f"Deleted {self.model_class.__name__} with id {entity_id}")
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__}: {e}")
            raise
    
    async def get_by_id(
        self,
        entity_id: UUID,
        loader_options: Optional[List[Any]] = None
    ) -> Optional[TEntity]:
        """Retrieve entity by ID with optional eager loading."""
        try:
            stmt = select(self.model_class).where(self.model_class.id == entity_id)
            if loader_options:
                for opt in loader_options:
                    stmt = stmt.options(opt)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self.mapper.to_entity(model) if model else None
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by id: {e}")
            raise

    async def list(
        self,
        filter_func: Optional[Union[Callable[[TEntity], bool], Dict[str, Any]]] = None,
        loader_options: Optional[List[Any]] = None
    ) -> List[TEntity]:
        """List entities with optional filtering and eager loading."""
        try:
            stmt = select(self.model_class)
            if loader_options:
                for opt in loader_options:
                    stmt = stmt.options(opt)
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            entities = [self.mapper.to_entity(model) for model in models]
            
            if filter_func is None:
                return entities
            if callable(filter_func):
                return [e for e in entities if filter_func(e)]
            if isinstance(filter_func, dict):
                filtered = entities
                for key, value in filter_func.items():
                    filtered = [e for e in filtered if getattr(e, key, None) == value]
                return filtered
            return entities
        except Exception as e:
            logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        loader_options: Optional[List[Any]] = None,
        order_by: Optional[Any] = None
    ) -> PaginatedResult[TEntity]:
        """
        List entities with pagination and filtering.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Dictionary of column_name: value for filtering
            loader_options: SQLAlchemy loader options for eager loading
            order_by: SQLAlchemy column for ordering (e.g., Model.created_at.desc())
        """
        try:
            # Base query
            stmt = select(self.model_class)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        stmt = stmt.where(getattr(self.model_class, key) == value)
            
            # Count total
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_count = await self.session.scalar(count_stmt)
            
            # Apply ordering
            if order_by is not None:
                stmt = stmt.order_by(order_by)
            
            # Apply eager loading
            if loader_options:
                for opt in loader_options:
                    stmt = stmt.options(opt)
            
            # Apply pagination
            offset = (page - 1) * page_size
            stmt = stmt.offset(offset).limit(page_size)
            
            # Execute
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            entities = [self.mapper.to_entity(model) for model in models]
            
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            
            return PaginatedResult(
                items=entities,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1
            )
        except Exception as e:
            logger.error(f"Error paginating {self.model_class.__name__}: {e}")
            raise
    
   
    async def find(
        self,
        predicate: Callable[[TEntity], bool],
        loader_options: Optional[List[Any]] = None
    ) -> List[TEntity]:
        """Find entities matching a predicate."""
        stmt = select(self.model_class)
        if loader_options:
            for opt in loader_options:
                stmt = stmt.options(opt)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        entities = [self.mapper.to_entity(m) for m in models]
        return [e for e in entities if predicate(e)]

    async def find_paginated(
        self,
        predicate: Callable[[TEntity], bool],
        page: int = 1,
        page_size: int = 10,
        loader_options: Optional[List[Any]] = None
    ) -> PaginatedResult[TEntity]:
        """Find entities matching a predicate with pagination."""
        # Note: This loads all matching entities into memory then paginates
        # For large datasets, prefer list_paginated with SQL filters
        all_entities = await self.find(predicate, loader_options)
        total_count = len(all_entities)
        
        # Paginate in memory
        start = (page - 1) * page_size
        end = start + page_size
        items = all_entities[start:end]
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )

    async def list_by_related_equal(
        self,
        related_model: Any,
        relationship_name: str,
        related_field: str,
        value: Any,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        eager: bool = True
    ) -> Union[List[TEntity], PaginatedResult[TEntity]]:
        """
        List entities by filtering on related model field.
        
        Args:
            related_model: Related SQLAlchemy model
            relationship_name: Relationship attribute name on primary model
            related_field: Column name on related model to filter
            value: Value to match
            page: Optional page number for pagination
            page_size: Optional page size for pagination
            eager: Whether to eager load the relationship
        """
        rel_attr = getattr(self.model_class, relationship_name)
        rel_col = getattr(related_model, related_field)
        
        stmt = select(self.model_class).join(rel_attr).where(rel_col == value)
        
        if eager:
            from sqlalchemy.orm import selectinload
            # Load the relationship and its nested tenant relationship
            stmt = stmt.options(
                selectinload(rel_attr).selectinload(related_model.tenant)
            )
        
        # Pagination
        if page is not None and page_size is not None:
            # Count total
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_count = await self.session.scalar(count_stmt)
            
            # Apply pagination
            offset = (page - 1) * page_size
            stmt = stmt.offset(offset).limit(page_size)
            
            result = await self.session.execute(stmt)
            entities = [self.mapper.to_entity(m) for m in result.scalars().all()]
            
            total_pages = (total_count + page_size - 1) // page_size
            
            return PaginatedResult(
                items=entities,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1
            )
        else:
            # No pagination
            result = await self.session.execute(stmt)
            return [self.mapper.to_entity(m) for m in result.scalars().all()]

    async def first_or_default(
        self,
        predicate: Optional[Callable[[TEntity], bool]] = None
    ) -> Optional[TEntity]:
        """Get first entity matching predicate or None."""
        query = select(self.model_class).limit(1)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        entity = self.mapper.to_entity(model)
        
        if predicate is None or predicate(entity):
            return entity
        
        # If predicate fails, search more records
        query = select(self.model_class)
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        for model in models:
            entity = self.mapper.to_entity(model)
            if predicate(entity):
                return entity
        
        return None
    
    async def single_or_default(
        self,
        predicate: Callable[[TEntity], bool]
    ) -> Optional[TEntity]:
        """Get single entity matching predicate."""
        query = select(self.model_class)
        result = await self.session.execute(query)
        models = result.scalars().all()
        entities = [self.mapper.to_entity(model) for model in models]
        
        matching = [e for e in entities if predicate(e)]
        
        if len(matching) == 0:
            return None
        elif len(matching) == 1:
            return matching[0]
        else:
            raise ValueError(f"Multiple entities found matching predicate. Expected 0 or 1, got {len(matching)}")
    
    async def any(
        self,
        predicate: Optional[Callable[[TEntity], bool]] = None
    ) -> bool:
        """Check if any entity matches predicate."""
        if predicate is None:
            query = select(func.count()).select_from(self.model_class).limit(1)
            result = await self.session.execute(query)
            return result.scalar() > 0
        
        # For complex predicates, fetch and check in-memory
        query = select(self.model_class).limit(1)
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        for model in models:
            entity = self.mapper.to_entity(model)
            if predicate(entity):
                return True
        
        return False
    
    async def count(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering."""
        try:
            stmt = select(func.count(self.model_class.id))
            if filter_dict:
                for key, value in filter_dict.items():
                    if hasattr(self.model_class, key):
                        stmt = stmt.where(getattr(self.model_class, key) == value)
            result = await self.session.execute(stmt)
            return result.scalar()
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise

    async def exists(self, entity_id: UUID) -> bool:
        """Check if an entity exists."""
        try:
            stmt = select(func.count(self.model_class.id)).where(self.model_class.id == entity_id)
            result = await self.session.execute(stmt)
            return result.scalar() > 0
        except Exception as e:
            logger.error(f"Error checking existence of {self.model_class.__name__}: {e}")
            raise
    async def order_by(
        self,
        key_selector: Callable[[TEntity], Any],
        descending: bool = False,
        predicate: Optional[Callable[[TEntity], bool]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TEntity]:
        """Order entities by key selector."""
        query = select(self.model_class).limit(limit).offset(offset)
        result = await self.session.execute(query)
        models = result.scalars().all()
        entities = [self.mapper.to_entity(model) for model in models]
        
        # Apply predicate if provided
        if predicate:
            entities = [e for e in entities if predicate(e)]
        
        # Sort in-memory using key selector
        return sorted(entities, key=key_selector, reverse=descending)
    
    async def select(
        self,
        selector: Callable[[TEntity], Any],
        predicate: Optional[Callable[[TEntity], bool]] = None
    ) -> List[Any]:
        """Project entities using selector."""
        query = select(self.model_class)
        result = await self.session.execute(query)
        models = result.scalars().all()
        entities = [self.mapper.to_entity(model) for model in models]
        
        # Apply predicate if provided
        if predicate:
            entities = [e for e in entities if predicate(e)]
        
        # Apply selector
        return [selector(e) for e in entities]
    
    def query(self) -> LinqQuery[TEntity, TModel]:
        """Create a LINQ-style query builder.
        
        Returns:
            LinqQuery instance for fluent query building
            
        Example:
            results = await (repository.query()
                .where(lambda x: x.status == NotificationStatus.SENT)
                .order_by(lambda x: x.created_at, "created_at")
                .skip(10)
                .take(20)
                .to_list())
        """
        return LinqQuery[TEntity, TModel](
            self.model_class,
            self.session,
            self.mapper
        )
    
    def where(self, predicate: Callable[[TEntity], bool]) -> LinqQuery[TEntity, TModel]:
        """Start a LINQ-style query with a where clause.
        
        Args:
            predicate: Lambda expression to filter entities
            
        Returns:
            LinqQuery instance for fluent query building
            
        Example:
            results = await (repository
                .where(lambda x: x.status == NotificationStatus.SENT)
                .order_by(lambda x: x.created_at)
                .to_list())
        """
        return self.query().where(predicate)

    # ---------------------------------------------------------------------
    # Advanced, generic, SQL-only deep query support
    # ---------------------------------------------------------------------
    def _apply_op(self, column, op: str, value: Any):
        op_l = (op or "eq").lower()
        if op_l == "eq":
            return column == value
        if op_l == "ne":
            return column != value
        if op_l == "gt":
            return column > value
        if op_l == "gte":
            return column >= value
        if op_l == "lt":
            return column < value
        if op_l == "lte":
            return column <= value
        if op_l == "like":
            return column.like(f"%{value}%")
        if op_l == "ilike":
            return column.ilike(f"%{value}%")
        if op_l == "in":
            seq = value if isinstance(value, (list, tuple, set)) else [value]
            return column.in_(seq)
        raise ValueError(f"Unsupported op: {op}")

    def _ensure_joins(self, stmt, root_model, rel_path: str, cache: Dict[str, Any]):
        if not rel_path:
            return stmt, root_model
        if rel_path in cache:
            return stmt, cache[rel_path]
        current = root_model
        built: List[str] = []
        for part in rel_path.split("."):
            built.append(part)
            key = ".".join(built)
            if key in cache:
                current = cache[key]
                continue
            rel_attr = getattr(current, part, None)
            if rel_attr is None or not hasattr(rel_attr, "property"):
                break
            target_cls = rel_attr.property.mapper.class_
            alias = aliased(target_cls)
            if current is root_model:
                stmt = stmt.join(alias, getattr(root_model, part))
            else:
                stmt = stmt.join(alias, getattr(current, part))
            cache[key] = alias
            current = alias
        cache[rel_path] = current
        return stmt, current

    def _resolve_path_column(self, stmt, root_model, path: str, cache: Dict[str, Any]):
        if "." not in path:
            return stmt, getattr(root_model, path)
        *rel_parts, field = path.split(".")
        rel_path = ".".join(rel_parts)
        stmt, alias = self._ensure_joins(stmt, root_model, rel_path, cache)
        return stmt, getattr(alias, field)

    def _get_pk_column(self):
        Model = self.model_class
        mapper = getattr(Model, "__mapper__", None)
        if mapper and mapper.primary_key:
            return mapper.primary_key[0]
        if hasattr(Model, "id"):
            return getattr(Model, "id")
        return None

    async def list_advanced_paginated(
        self,
        page: int,
        page_size: int,
        *,
        root_filters: Optional[Dict[str, Any]] = None,
        related_filters: Optional[List[Any]] = None,
        includes: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_direction: str = "desc",
        search_text: Optional[str] = None,
        search_fields: Optional[List[str]] = None
    ) -> PaginatedResult[TEntity]:
        Model = self.model_class
        stmt = select(Model)
        join_cache: Dict[str, Any] = {}

        if includes:
            for inc in includes:
                parts = inc.split(".")
                # Build loader option using class-bound attributes
                try:
                    first_attr = getattr(Model, parts[0])
                except AttributeError:
                    continue
                opt = selectinload(first_attr)
                current_cls = first_attr.property.mapper.class_
                for p in parts[1:]:
                    try:
                        sub_attr = getattr(current_cls, p)
                    except AttributeError:
                        sub_attr = None
                    if sub_attr is None:
                        break
                    opt = opt.selectinload(sub_attr)
                    current_cls = sub_attr.property.mapper.class_
                stmt = stmt.options(opt)

        if root_filters:
            for key, value in root_filters.items():
                if hasattr(Model, key):
                    stmt = stmt.where(getattr(Model, key) == value)

        if related_filters:
            for rf in related_filters:
                if isinstance(rf, (list, tuple)) and len(rf) == 4:
                    rel_path, field, op, value = rf
                    full_path = f"{rel_path}.{field}" if rel_path else field
                    stmt, col = self._resolve_path_column(stmt, Model, full_path, join_cache)
                    stmt = stmt.where(self._apply_op(col, op, value))

        if search_text and search_fields:
            clauses = []
            for fpath in search_fields:
                stmt, col = self._resolve_path_column(stmt, Model, fpath, join_cache)
                clauses.append(col.ilike(f"%{search_text}%"))
            if clauses:
                stmt = stmt.where(or_(*clauses))

        if sort_by:
            stmt, sort_col = self._resolve_path_column(stmt, Model, sort_by, join_cache)
            if sort_col is not None:
                stmt = stmt.order_by(desc(sort_col) if (sort_direction or "desc").lower() == "desc" else asc(sort_col))

        # Build count over the filtered (pre-pagination) statement
        pk_col = self._get_pk_column()
        base_for_count = stmt.order_by(None)
        if pk_col is not None:
            count_subq = base_for_count.with_only_columns(pk_col).distinct().subquery()
            count_stmt = select(func.count()).select_from(count_subq)
        else:
            count_stmt = select(func.count()).select_from(base_for_count.subquery())
        total_count = await self.session.scalar(count_stmt)

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        entities = [self.mapper.to_entity(m) for m in models]

        total_pages = (total_count + page_size - 1) // page_size
        return PaginatedResult(
            items=entities,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )