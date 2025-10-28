
from select import select
from notification_service.domain.interfaces import IGenericRepository, T
class GenericRepository(IGenericRepository[T]):
    async def __init__(self, session):
        self.session = session

    async def get_by_id(self, entity_id: int) -> T | None:
        return await self.session.get(self._get_entity_class(), entity_id)

    async def get_all(self) -> list[T]:
        result = await self.session.execute(select(self._get_entity_class()))
        return result.scalars().all()

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity_id: int) -> bool:
        entity = await self.get_by_id(entity_id)
        if entity:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        return False

    def _get_entity_class(self):
        return self.__orig_bases__[0].__args__[0]