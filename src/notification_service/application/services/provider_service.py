from notification_service.domain.interfaces.iunit_of_work  import IUnitOfWork
from notification_service.domain.entities.providers_supported import Provider
from uuid import UUID
from notification_service.adpaters.inbound.dto.provider_supported_dto import TestRequestDto
from notification_service.Infrastructure.providers.sms.kifiya_sms_gateway import KifiyaSMSGateway
from notification_service.domain.value_objects.notification_response import ProviderTestResponse


class ProviderService:
    
    def  __init__(self,uow:IUnitOfWork,kifiya_sms_gateway:KifiyaSMSGateway):
        self.uow = uow
        self.kifiya_sms_gateway = kifiya_sms_gateway
    async def create_provider(self, provider:Provider) -> Provider:
        async with self.uow:
            created_provider = await self.uow.providers.add(provider)
            await self.uow.commit()
            return created_provider
     
    
    async def get_all(self)-> list[Provider]:
        async with self.uow:
            providers = await self.uow.providers.list()
            return providers
    
    async def get_providers_by_channel(self,channel:str)->list[Provider]:
        
        async with self.uow:
            providers = await self.uow.providers.list(lambda p: p.channel == channel)
            return providers
    
    async def get_provider_by_name(self,name:str)->Provider:
        async with self.uow:
            provider = await self.uow.providers.first_or_default(lambda p: p.name == name)
            return provider
    
    async def update(self,provider:Provider)->Provider:
        async with self.uow:
            updated_provider = await self.uow.providers.update(provider)
            await self.uow.commit()
            return updated_provider
    
    async def delete(self,id:UUID):
        
        async with self.uow:
            await self.uow.providers.delete(id)
            await self.uow.commit()
    async def test_provider(self, dto:TestRequestDto)->ProviderTestResponse:
        # Implement the logic to test the provider with the given configuration
        match dto.channel:
            case "sms":
                # Add SMS provider testing logic here
                return await self.kifiya_sms_gateway.test(dto.config, dto.address)
                pass
            case "email":
                # Add Email provider testing logic here
                pass
            case _:
                raise ValueError(f"Unsupported channel: {dto.channel}")
                pass
        return False
            