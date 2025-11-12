from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.providers_supported import Provider
from uuid import UUID
from typing import List, Optional, Dict, Any
from notification_service.adapters.inbound.dto.provider_supported_dto import TestRequestDto, ProviderResponseDTO
from notification_service.infrastructure.providers.sms.kifiya_sms_gateway import KifiyaSMSGateway
from notification_service.domain.value_objects.notification_response import ProviderTestResponse
from notification_service.application.services.base_service import BaseService


class ProviderService(BaseService[Provider, ProviderResponseDTO]):
    
    def __init__(self, uow: IUnitOfWork, kifiya_sms_gateway: KifiyaSMSGateway):
        super().__init__(uow, Provider, ProviderResponseDTO)
        self.uow = uow
        self.kifiya_sms_gateway = kifiya_sms_gateway
    
    def _get_repository(self):
        """Get providers repository."""
        return self.uow.providers
    
    def _get_default_search_fields(self) -> Optional[List[str]]:
        """Get default search fields for providers."""
        return ["providerName", "displayName", "channel"]
    
    def _build_related_filters(self, params) -> List:
        """Build related filters for providers."""
        # Providers don't have related filters by default
        return []
    
    def _extract_custom_filters(self, params) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        if hasattr(params, 'channel') and params.channel:
            filters["channel"] = params.channel
        if hasattr(params, 'isActive') and params.isActive is not None:
            filters["isActive"] = params.isActive
        return filters
    async def create(self, provider: Provider) -> Provider:
        """Create a new provider."""
        async with self.uow:
            created_provider = await self.uow.providers.add(provider)
            await self.uow.commit()
            return created_provider
    
    # Keep old method for backward compatibility
    async def create_provider(self, provider: Provider) -> Provider:
        """Create a new provider (deprecated - use create() instead)."""
        return await self.create(provider)
    
    # Keep old methods for backward compatibility
    async def get_all(self) -> list[Provider]:
        """Get all providers (deprecated - use get() instead)."""
        async with self.uow:
            providers = await self.uow.providers.list()
            return providers
    
    async def get_providers_by_channel(self, channel: str) -> list[Provider]:
        """Get providers by channel (custom method)."""
        async with self.uow:
            providers = await self.uow.providers.list(lambda p: p.channel == channel)
            return providers
    
    async def get_provider_by_name(self, name: str) -> Provider:
        """Get provider by name (custom method)."""
        async with self.uow:
            provider = await self.uow.providers.firstOrDefault(lambda p: p.providerName == name)
            return provider
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
            