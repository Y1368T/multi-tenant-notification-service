from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, PaginatedRequestDTO, RelatedFilter
from notification_service.application.services.tenant_sms_configuration_service import TenantSMSConfigurationService
from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from fastapi import APIRouter, Depends
from uuid import UUID
from notification_service.adapters.inbound.dto.tenant_sms_confuguration_request_dto import TenantSMSConfigurationRequestDto
@api_controller(prefix="/tenant-sms-configurations", tags=["Tenant SMS Configurations"])
class TenantSMSConfigurationController(ControllerBase):
    
    def __init__(self, tenant_sms_configuration_service:TenantSMSConfigurationService = Depends()):
        self.tenant_sms_configuration_service = tenant_sms_configuration_service
        
    @get("/get_by_tenant_id/{tenant_id}")
    async def get_tenant_sms_configuration(self, tenant_id: UUID):
        sms_config = await self.tenant_sms_configuration_service.get_configuration_by_tenant_id(tenant_id)
        return sms_config
    
    @post("/create")
    async def create_tenant_sms_configuration(self, request_dto: TenantSMSConfigurationRequestDto):
        entity = request_dto.toEntity()
        created_config = await self.tenant_sms_configuration_service.create_configuration(entity)
        return created_config
    
    @put("/update/{config_id}")
    async def update_tenant_sms_configuration(self, config_id: str, request_dto: TenantSMSConfigurationRequestDto):
        entity = request_dto.toEntity()
        updated_config = await self.tenant_sms_configuration_service.update_configuration(config_id, entity)
        return updated_config
    
    @delete("/delete/{config_id}")
    async def delete_tenant_sms_configuration(self, config_id: str):
        await self.tenant_sms_configuration_service.delete_configuration(config_id)
        return {"message": "Tenant SMS Configuration deleted successfully"}
    
    @get("get_by_id/{config_id}")
    async def get_tenant_sms_configuration_by_id(self, config_id: UUID):
        sms_config = await self.tenant_sms_configuration_service.get_configuration_by_id(config_id)
        return sms_config
    
    
    @get("/get_by_filter")
    async def get_tenant_sms_configuration_by_filter(self, params: PaginatedRequestDTO = Depends()):
        default_search_fields = [
            "provider_name"
        ]
        root_filters = {"tenant_id": params.tenant_id} if params.tenant_id else {}
        related_filters: list[RelatedFilter] = []

        req = PaginatedRequest(
            page=params.page,
            page_size=params.page_size,
            sort_by="created_at",
            sort_direction=params.sort_direction,
            search=params.search,
            search_fields=default_search_fields,
            filters=root_filters,                    # add fixed root filters here if needed
            related_filters=related_filters if related_filters else []
        )
        sms_config = await self.tenant_sms_configuration_service.get_all_configurations_advanced(req)
        return sms_config