"""Generic repository implementation."""
import logging
from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.igeneric_repository import IGenericRepository

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
        """Add new entity to repository.
        
        Args:
            entity: Domain entity to persist
            
        Returns:
            Persisted entity with generated ID
        """
        try:
            model = self.mapper.to_model(entity)
            self.session.add(model)
            await self.session.flush()
            await self.session.refresh(model)
            logger.debug(f"Added {self.model_class.__name__} with id {model.id}")
            return self.mapper.to_entity(model)
        except Exception as e:
            logger.error(f"Error adding {self.model_class.__name__}: {e}")
            raise

    async def update(self, entity: TEntity) -> TEntity:
        """Update existing entity.
        
        Args:
            entity: Domain entity with updated values
            
        Returns:
            Updated entity
        """
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == entity.id)
        )
        model= result.scalar_one_or_none()
        if not model:
            raise ValueError(f"{self.model_class.__name__} with id {entity.id} not found for update")
        # Update model fields from entity
        updated_model=self.mapper.update_model_from_entity(model, entity)
        await self.session.flush()
        await self.session.refresh(updated_model)
        
        #convert back to entity and return
        return self.mapper.to_entity(updated_model)

    async def delete(self, entity_id: UUID) -> None:
        """Delete entity by ID.
        
        Args:
            entity_id: Entity identifier
        """
        
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == entity_id)
        )
        
        return result.rowcount > 0  
      
    
    async def get_by_id(self, entity_id: UUID) -> Optional[TEntity]:
        """Retrieve entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Domain entity if found, None otherwise
        """
        try:
            result = await self.session.get(self.model_class, entity_id)
            if result is None:
                return None
            return self.mapper.to_entity(result)
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by id {entity_id}: {e}")
            raise
    
    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TEntity]:
        """List entities with optional filtering and pagination.
        
        Args:
            filters: Filter conditions (e.g., {"status": "pending"})
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of domain entities`
        """
        try:
            query = select(self.model_class)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.where(getattr(self.model_class, key) == value)
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            result = await self.session.execute(query)
            return self.mapper.to_list_of_entities(result.scalars().all())
        
        except Exception as e:
            logger.error(f"Error listing {self.model_class.__name__}: {e}")
            raise     