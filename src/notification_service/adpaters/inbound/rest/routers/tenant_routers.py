
from fastapi import APIRouter
from fastapi import Depends, Request
from notification_service.application.services.tenant_service import TenantService
from notification_service.Infrastructure.persisitence.db_session.session import Database
from notification_service.Infrastructure.persisitence.unit_of_work import UnitOfWork
from uuid import UUID, uuid4
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adpaters.inbound.dto.tenant_request_dto import TenantRequestDTO
from notification_service.config.settings import settings
from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete


@api_controller(prefix="/tenants", tags=["Tenants"])
class TenantController(ControllerBase):
    """Controller for tenant-related endpoints."""
    def __init__(self, tenant_service: TenantService = Depends()):
        self.tenant_service = tenant_service
        
        


    @get("/get_by_id/{tenant_id}")
    async def get_tenant(self, tenant_id: UUID):
        tenant = await self.tenant_service.get_tenant_by_id(tenant_id)
        return tenant

    @post("/create")
    async def create_tenant(self,tenant_data: TenantRequestDTO):
        tenantentity=Tenant(
            name=tenant_data.name,
            prefix=tenant_data.prefix,
            is_active=tenant_data.is_active,
            id=uuid4()
        )
        tenantentity = await self.tenant_service.create_tenant(tenantentity)
        return tenantentity
    
    @get("/getall")
    async def get_all_tenants(self):
        tenants = await self.tenant_service.list_all_tenants()
        return tenants
    
    @put("/update/{tennat_id}")
    async def update(self,tenant_id:UUID, tenant:Tenant):
        tenant=await self.tenant_service.update_tenant(tenant_id,tenant)
        return tenant

    @delete("/delete/{tenant_id}")
    async def delete_tenant(self, tenant_id: UUID):
        await self.tenant_service.delete_tenant(tenant_id)
        return {"message": "Tenant deleted successfully"}