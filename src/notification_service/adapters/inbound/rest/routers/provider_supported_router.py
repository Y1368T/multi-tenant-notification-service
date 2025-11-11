from qena_shared_lib.http import ControllerBase,api_controller,get,post,delete,put
from notification_service.application.services.provider_service import ProviderService
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from notification_service.adapters.inbound.dto.provider_supported_dto import ProviderSupportedDTO,TestRequestDto
from uuid import UUID
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)
@api_controller(prefix="/provider-supported", tags=["Provider Supported"])
class ProviderSupportedController(ControllerBase):
    
    def __init__(self,provider_service:ProviderService = Depends()):
        self.provider_service = provider_service
        
    @get("/get_by_channel")
    async def get_by_channel(self, channel: str):
        return await self.provider_service.get_providers_by_channel(channel)
    
    @post("/create")
    async def create(self, provider_supported_dto: ProviderSupportedDTO):
        provider_supported=provider_supported_dto.toEntity()
        try :
            await self.provider_service.create_provider(provider_supported)
        except Exception as e:
            logger.error(f"Error creating provider supported: {e}")
            raise e
            
        return provider_supported
    
    @get("/get_all")
    async def get_all(self):
        return await self.provider_service.get_all()
    
    @delete("/delete/{id}")
    async def delete(self, id: UUID):
        return await self.provider_service.delete(id)
    
    @post("/test")
    async def test_provider(self, dto:TestRequestDto)->ProviderTestResponse:
        return await self.provider_service.test_provider(dto)