from sqlalchemy import select, func,delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, Type, TypeVar, List, Optional, Dict, Any, Callable,Union
from uuid import UUID
from notification_service.domain.interfaces.igeneric_repository import IGenericRepository
import logging


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
    
    async def get_by_id(self, entity_id: UUID) -> Optional[TEntity]:
        """Retrieve entity by ID."""
        try:
            query = select(self.model_class).where(self.model_class.id == entity_id)
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()
            if model:
                return self.mapper.to_entity(model)
            return None
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by id: {e}")
            raise
    
    async def list(self, filter_func: Optional[Union[Callable[[TEntity], bool], Dict[str, Any]]] = None) -> List[TEntity]:
        """
        List entities with optional filtering.
        
        Args:
            filter_func: Either a callable that takes an entity and returns bool,
                        or a dict of field names and values to filter by
        """
        try:
            result = await self.session.execute(select(self.model_class))
            models = result.scalars().all()
            entities = [self.mapper.to_entity(model) for model in models]
            
            if filter_func is None:
                return entities
            
            # Handle callable filter (lambda function)
            if callable(filter_func):
                return [e for e in entities if filter_func(e)]
            
            # Handle dict filter
            if isinstance(filter_func, dict):
                filtered = entities
                for key, value in filter_func.items():
                    filtered = [e for e in filtered if getattr(e, key, None) == value]
                return filtered
            
            return entities
        except Exception as e:
            logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise
    
    async def find(
        self,
        predicate: Callable[[TEntity], bool]
    ) -> List[TEntity]:
        """Find entities matching predicate."""
        query = select(self.model_class)
        result = await self.session.execute(query)
        models = result.scalars().all()
        entities = [self.mapper.to_entity(model) for model in models]
        
        # Apply predicate in-memory (for complex business logic)
        return [e for e in entities if predicate(e)]
    
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
    
    async def count(
        self,
        predicate: Optional[Callable[[TEntity], bool]] = None
    ) -> int:
        """Count entities matching predicate."""
        if predicate is None:
            query = select(func.count()).select_from(self.model_class)
            result = await self.session.execute(query)
            return result.scalar()
        
        # For complex predicates, fetch and count in-memory
        query = select(self.model_class)
        result = await self.session.execute(query)
        models = result.scalars().all()
        entities = [self.mapper.to_entity(model) for model in models]
        
        return sum(1 for e in entities if predicate(e))
    
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