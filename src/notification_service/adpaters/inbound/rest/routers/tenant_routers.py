
from fastapi import APIRouter
from fastapi import Depends, Request
from notification_service.application.services.tenant_service import TenantService
from notification_service.Infrastructure.persisitence.db_session.session import Database
from notification_service.Infrastructure.persisitence.unit_of_work import UnitOfWork
from uuid import UUID
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adpaters.inbound.dto.tenant_request_dto import TenantRequestDTO
from notification_service.config.settings import settings
from qena_shared_lib.http import ControllerBase,get,post,api_controller


@api_controller(prefix="/tenants", tags=["Tenants"])
class TenantController(ControllerBase):
    """Controller for tenant-related endpoints."""
    def __init__(self, tenant_service: TenantService = Depends()):
        self.tenant_service = tenant_service
        
        


    @get("/tenants/{tenant_id}")
    async def get_tenant(self, tenant_id: UUID):
        tenant = await self.tenant_service.get_tenant_by_id(tenant_id)
        return tenant

    @post("/create/")
    async def create_tenant(self,tenant_data: TenantRequestDTO):
        tenant = await self.tenant_service.create_tenant(tenant_data)
        return tenant