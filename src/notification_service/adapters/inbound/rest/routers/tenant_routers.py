from fastapi import APIRouter
from fastapi import Depends, Query
from notification_service.application.services.tenant_service import TenantService
from notification_service.infrastructure.persisitence.db_session.session import Database
from notification_service.infrastructure.persisitence.unit_of_work import UnitOfWork
from uuid import UUID, uuid4
from notification_service.domain.entities.tenant.tenant import Tenant
from notification_service.adapters.inbound.dto.tenant_request_dto import TenantRequestDTO
from notification_service.config.settings import settings
from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, PaginatedRequestDTO, RelatedFilter
from typing import Optional

@api_controller(prefix="/tenants", tags=["Tenants"])
class TenantController(ControllerBase):
    """Controller for tenant-related endpoints."""
    def __init__(self, tenant_service: TenantService):
        self.tenant_service = tenant_service
        
        


    @get("/get_by_id/{tenant_id}")
    async def get_tenant(self, tenant_id: UUID):
        tenant = await self.tenant_service.get_tenant_by_id(tenant_id)
        return tenant

    @post("/create")
    async def create_tenant(self,tenant_data: TenantRequestDTO):
        if(tenant_data.prefered_communication_method not in ["rest", "kafka", "rabbitmq", "grpc"]):
            raise ValueError("Invalid preferred communication method")
        
        tenantentity=Tenant(
            name=tenant_data.name,
            prefix=tenant_data.prefix,
            is_active=tenant_data.is_active,
            supported_channels=tenant_data.supported_channels,
            prefered_communication_method=tenant_data.prefered_communication_method,
            id=uuid4()
        )
        tenantentity = await self.tenant_service.create_tenant(tenantentity)
        return tenantentity
    
    @get("/getall")
    async def get_all_tenants(self,status: Optional[str] = Query(None, description="Filter by tenant status"),params: PaginatedRequestDTO = Depends()):   
        default_search_fields = [
            "name",
            "prefix",
        ]

        root_filters = {"status": status} if status else {}
        related_filters: list[RelatedFilter] = []
        if params.tenant_id:
           root_filters["tenant_id"] = params.tenant_id
        req = PaginatedRequest(
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by or "created_at",
            sort_direction=params.sort_direction,
            search_text=params.search,
            search_fields=default_search_fields,
            filters=root_filters,
            related_filters=related_filters if related_filters else []
        )
        tenants = await self.tenant_service.get_all_tenants_advanced(req)
        return tenants
    
    @put("/update/{tenant_id}")
    async def update(self,tenant_id:UUID, tenant:Tenant):
        tenant=await self.tenant_service.update_tenant(tenant_id,tenant)
        return tenant

    @delete("/delete/{tenant_id}")
    async def delete_tenant(self, tenant_id: UUID):
        await self.tenant_service.delete_tenant(tenant_id)
        return {"message": "Tenant deleted successfully"}