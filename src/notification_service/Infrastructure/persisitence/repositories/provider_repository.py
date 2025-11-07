from notification_service.domain.interfaces.igeneric_repository import IGenericRepository
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.domain.entities.providers_supported import Provider
from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.Infrastructure.persisitence.models.providers_supported import ProviderModel
from notification_service.Infrastructure.persisitence.mappers.provider_mapper import ProviderMapper

class ProviderRepository(GenericRepository[ProviderModel, Provider]):
    def __init__(self, session: AsyncSession):
       super().__init__(session, ProviderModel, ProviderMapper())