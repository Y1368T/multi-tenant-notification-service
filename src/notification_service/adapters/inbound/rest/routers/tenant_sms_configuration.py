from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, PaginatedRequestDTO, RelatedFilter
from notification_service.application.services.tenant_sms_configuration_service import TenantSMSConfigurationService
from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from fastapi import APIRouter, Depends
from uuid import UUID
from notification_service.adapters.inbound.dto.tenant_sms_confuguration_request_dto import TenantSMSConfigurationRequestDto
@api_controller(prefix="/tenant-sms-configurations", tags=["Tenant SMS Configurations"])
class TenantSMSConfigurationController(ControllerBase):
    
    def __init__(self, tenantSmsConfigurationService:TenantSMSConfigurationService = Depends()):
        self.tenantSmsConfigurationService = tenantSmsConfigurationService
        
    @get("/get_by_tenant_id/{tenant_id}")
    async def getTenantSmsConfiguration(self, tenant_id: UUID):
        smsConfig = await self.tenantSmsConfigurationService.getConfigurationByTenantId(tenant_id)
        return smsConfig
    
    @post("/create")
    async def createTenantSmsConfiguration(self, requestDto: TenantSMSConfigurationRequestDto):
        entity = requestDto.toEntity()
        createdConfig = await self.tenantSmsConfigurationService.createConfiguration(entity)
        return createdConfig
    
    @put("/update/{config_id}")
    async def updateTenantSmsConfiguration(self, config_id: str, requestDto: TenantSMSConfigurationRequestDto):
        entity = requestDto.toEntity()
        updatedConfig = await self.tenantSmsConfigurationService.updateConfiguration(entity)
        return updatedConfig
    
    @delete("/delete/{config_id}")
    async def deleteTenantSmsConfiguration(self, config_id: str):
        await self.tenantSmsConfigurationService.deleteConfiguration(config_id)
        return {"message": "Tenant SMS Configuration deleted successfully"}
    
    @get("getById/{config_id}")
    async def getTenantSmsConfigurationById(self, config_id: UUID):
        smsConfig = await self.tenantSmsConfigurationService.getConfigurationById(config_id)
        return smsConfig
    
    
    @get("/get_by_filter")
    async def getTenantSmsConfigurationByFilter(self, params: PaginatedRequestDTO = Depends()):
        defaultSearchFields = [
            "providerName"
        ]
        rootFilters = {"tenantId": params.tenantId} if params.tenantId else {}
        relatedFilters: list[RelatedFilter] = []

        req = PaginatedRequest(
            page=params.page,
            pageSize=params.pageSize,
            sortBy="createdAt",
            sortDirection=params.sortDirection,
            searchText=params.search,
            searchFields=defaultSearchFields,
            filters=rootFilters,
            relatedFilters=relatedFilters if relatedFilters else []
        )
        smsConfig = await self.tenantSmsConfigurationService.getAllConfigurationsAdvanced(req)
        return smsConfig