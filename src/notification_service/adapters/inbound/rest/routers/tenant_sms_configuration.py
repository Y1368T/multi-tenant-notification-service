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
    
    
    