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
    def __init__(self, tenantService: TenantService):
        self.tenantService = tenantService
        

    

    @get("/getById/{tenant_id}")
    async def getTenant(self, tenant_id: UUID):
        tenant = await self.tenantService.getTenantById(tenant_id)
        return tenant

    @post("/create")
    async def createTenant(self,tenantData: TenantRequestDTO):
        if(tenantData.preferedCommunicationMethod not in ["rest", "kafka", "rabbitmq", "grpc"]):
            raise ValueError("Invalid preferred communication method")
        
        tenantEntity=Tenant(
            name=tenantData.name,
            prefix=tenantData.prefix,
            isActive=tenantData.isActive,
            supportedChannels=tenantData.supportedChannels,
            preferedCommunicationMethod=tenantData.preferedCommunicationMethod,
            id=uuid4()
        )
        tenantEntity = await self.tenantService.createTenant(tenantEntity)
        return tenantEntity
    
    @get("/getall")
    async def getAllTenants(self,status: Optional[str] = Query(None, description="Filter by tenant status"),params: PaginatedRequestDTO = Depends()):   
        defaultSearchFields = [
            "name",
            "prefix",
        ]

        rootFilters = {"status": status} if status else {}
        relatedFilters: list[RelatedFilter] = []
        if params.tenantId:
           rootFilters["tenantId"] = params.tenantId
        req = PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy=params.sortBy or "createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=defaultSearchFields,
            filters=rootFilters,
            relatedFilters=relatedFilters if relatedFilters else []
        )
        tenants = await self.tenantService.getAllTenantsAdvanced(req)
        return tenants
    
    @put("/update/{tenant_id}")
    async def update(self,tenant_id:UUID, tenant:Tenant):
        tenant=await self.tenantService.updateTenant(tenant_id,tenant)
        return tenant

    @delete("/delete/{tenant_id}")
    async def deleteTenant(self, tenant_id: UUID):
        await self.tenantService.deleteTenant(tenant_id)
        return {"message": "Tenant deleted successfully"}