from typing import List,Optional
from uuid import UUID
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.domain.interfaces import IUnitOfWork
from notification_service.infrastructure.messaging.rabbitmq import RabbitMQConsumer
from notification_service.domain.interfaces.imessage_consumer import IMessageConsumer
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.tenant_request_dto import TenantResponseDTO
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest

class TenantService:
    def __init__(self, uow: IUnitOfWork,rabbitmqConsumer:IMessageConsumer):
        self.uow = uow
        self.rabbitmqConsumer=rabbitmqConsumer
    
        
        
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
    async def createTenant(self, tenant: Tenant) -> Tenant:
        """Create a new tenant.
        
        Args:
            tenant: Tenant entity to create
            
        Returns:
            Created Tenant entity with generated ID
        """
        async with self.uow:
            createdTenant: Tenant = await self.uow.tenants.add(tenant)
            await self.uow.commit()
            if(createdTenant.preferedCommunicationMethod == "rabbitmq" and createdTenant.isActive and createdTenant.supportedChannels and self.rabbitmqConsumer):
                # Additional logic for rabbitmq preferred communication method can be added here
                for channel in createdTenant.supportedChannels:
                    queueName = f"notification.{channel}.{createdTenant.prefix}"
                    # Here you might want to initialize or configure the queue for the tenant
                    await self.rabbitmqConsumer.ensureQueueExistsAndSubscribe(queueName=queueName,channel=channel)
                    pass
                
            return createdTenant
    async def updateTenant(self, tenantId: UUID, tenant: Tenant) -> Tenant:
        """Update an existing tenant.
        
        Args:
            tenantId: Tenant identifier
            tenant: Tenant entity with updated values
            
        Returns:
            Updated Tenant entity
        """
        async with self.uow:
            updatedTenant = await self.uow.tenants.update(tenant)
            await self.uow.commit()
            return updatedTenant
    async def deleteTenant(self, tenantId: UUID) -> None:
        """Delete a tenant by its ID.
        
        Args:
            tenantId: Tenant identifier
        """
        async with self.uow:
            await self.uow.tenants.delete(tenantId)
            await self.uow.commit()
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
    
    async def getAllTenantsAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[TenantResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        """
        async with self.uow:
            
            relatedFiltersTuples = [
            (rf.relationshipPath, rf.field, rf.op.value if hasattr(rf.op, 'value') else str(rf.op), rf.value)
            for rf in (req.relatedFilters or [])
            ]
            result = await self.uow.tenants.listAdvancedPaginated(
                page=req.page,
                pageSize=req.pageSize,
                rootFilters=req.filters or {},
                relatedFilters=relatedFiltersTuples,
                includes=[],
                sortBy=req.sortBy,
                sortDirection=req.sortDirection.value,
                searchText=req.searchText,
                searchFields=req.searchFields or []
            )

            dtoItems = [
                TenantResponseDTO.fromEntityWithRelations(notification)
                for notification in result.items
            ]

            return PaginatedResponseDTO(
                items=dtoItems,
                page=result.page,
                pageSize=result.pageSize,
                totalCount=result.totalCount,
                totalPages=result.totalPages,
                hasNext=result.hasNext,
                hasPrevious=result.hasPrevious
            )
    