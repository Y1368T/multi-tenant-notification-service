from typing import List, Optional, Dict, Any
from uuid import UUID
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.domain.interfaces import IUnitOfWork
from notification_service.infrastructure.messaging.rabbitmq import RabbitMQConsumer
from notification_service.domain.interfaces.imessage_consumer import IMessageConsumer
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.tenant_request_dto import TenantResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import (
    PaginatedRequest,
    PaginatedRequestDTO,
    RelatedFilter,
    FilterOp
)
from notification_service.application.services.base_service import BaseService

class TenantService(BaseService[Tenant, TenantResponseDTO]):
    def __init__(self, uow: IUnitOfWork, rabbitmqConsumer: IMessageConsumer):
        super().__init__(uow, Tenant, TenantResponseDTO)
        self.rabbitmqConsumer = rabbitmqConsumer
    
    def _get_repository(self):
        """Get tenants repository."""
        return self.uow.tenants
    
    def _extract_custom_filters(self, params: PaginatedRequestDTO) -> Dict[str, Any]:
        """Extract custom filters from request DTO."""
        filters = {}
        # Check if params has status attribute (TenantFilterDTO extends PaginatedRequestDTO)
        if hasattr(params, 'status') and params.status:
            filters["status"] = params.status
        return filters
    
    def _build_related_filters(self, params: PaginatedRequestDTO) -> List[RelatedFilter]:
        """Build related filters for tenants."""
        # Tenants don't have related filters by default
        return []
    
        
        
    async def getTenantByPrefix(self, prefix: str ) -> Optional[Tenant]:
        """Retrieve tenant by its prefix.
        
        Args:
            prefix: Tenant prefix string
            
        Returns:
            Tenant entity if found, None otherwise
        """
        async with self.uow:
            tenant = await self.uow.tenants.getTenantByPrefix(prefix)
            return tenant
    async def listAllTenants(self) -> List[Tenant]:
        """List all tenants in the system.
        
        Returns:
            List of Tenant entities
        """
        async with self.uow:
            tenants = await self.uow.tenants.list()
            return tenants
    async def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant with RabbitMQ queue setup.
        
        Args:
            tenant: Tenant entity to create
            
        Returns:
            Created Tenant entity with generated ID
        """
        # Call base create method to handle the standard creation logic
        createdTenant = await super().create(tenant)
        
        # Add custom RabbitMQ queue setup logic
        if(createdTenant.preferedCommunicationMethod == "rabbitmq" and createdTenant.isActive and createdTenant.supportedChannels and self.rabbitmqConsumer):
            # Additional logic for rabbitmq preferred communication method can be added here
            for channel in createdTenant.supportedChannels:
                queueName = f"notification.{channel}.{createdTenant.prefix}"
                # Here you might want to initialize or configure the queue for the tenant
                await self.rabbitmqConsumer.ensureQueueExistsAndSubscribe(queueName=queueName,channel=channel)
        
        return createdTenant
    
    # Keep old method for backward compatibility during migration
    async def createTenant(self, tenant: Tenant) -> Tenant:
        """Create a new tenant (deprecated - use create() instead)."""
        return await self.create(tenant)
    # Keep old methods for backward compatibility during migration
    async def updateTenant(self, tenantId: UUID, tenant: Tenant) -> Tenant:
        """Update an existing tenant (deprecated - use update() instead)."""
        tenant.id = tenantId
        return await self.update(tenant)
    
    async def deleteTenant(self, tenantId: UUID) -> None:
        """Delete a tenant by its ID (deprecated - use delete() instead)."""
        await self.delete(tenantId)
    
    async def getTenantById(self, tenantId: UUID) -> Optional[Tenant]:
        """Retrieve tenant by its ID.
        
        Args:
            tenantId: Tenant identifier
            
        Returns:
            Tenant entity if found, None otherwise
        """
        async with self.uow:
            tenant = await self.uow.tenants.getById(tenantId)
            return tenant
    async def getTenantsBySupportedChannel(self, channel: str) -> List[Tenant]:
        """Retrieve tenants that support a specific channel.
        
        Args:
            channel: Channel name (e.g., 'email', 'sms')
            
        Returns:
            List of Tenant entities that support the specified channel
        """
        async with self.uow:
            tenants = await self.uow.tenants.getTenantsBySupportedChannel(channel)
            return tenants
    async def getActiveTenants(self) -> List[Tenant]:
        """Retrieve all active tenants.
        
        Returns:
            List of active Tenant entities
        """
        async with self.uow:
            tenants = await self.uow.tenants.find(lambda t: t.isActive)
            return tenants
    
    async def getTenantsForRabbitmq(self)->list[Tenant]:
        
        async with self.uow:
            tenants = await self.uow.tenants.find(lambda t: t.preferedCommunicationMethod == "rabbitmq" 
                                                  and t.isActive)
            return tenants
    
    # Keep old method for backward compatibility during migration
    async def getAllTenantsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[TenantResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        (Deprecated - use get() instead)
        """
        # Convert PaginatedRequest to PaginatedRequestDTO
        from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequestDTO, SortDirection
        params = PaginatedRequestDTO(
            page=req.page,
            pageSize=req.pageSize,
            sortBy=req.sortBy,
            sortDirection=req.sortDirection,
            search=req.searchText,
            tenantId=None
        )
        # Manually set filters from req.filters
        if req.filters:
            if 'status' in req.filters:
                params.status = req.filters['status']
        return await self.get(params)
    