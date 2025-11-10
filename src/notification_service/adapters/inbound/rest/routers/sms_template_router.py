from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from notification_service.application.services.sms_template_service import SMSTemplateService
from notification_service.adapters.inbound.dto.sms_template_request_dto import SMSTemplateRequestDTO,SMSTemplateFilters
from uuid import UUID

@api_controller(prefix="/sms-templates", tags=["SMS Templates"])
class SMSTemplateController(ControllerBase):
    
    def __init__(self, sms_template_service: SMSTemplateService):
        self.sms_template_service = sms_template_service
    
    @post("/create")
    async def create_sms_template(self, template:SMSTemplateRequestDTO):
        """Create a new SMS template."""
        entity=template.to_entity()
        return await self.sms_template_service.create_sms_template(entity)
    
    @get("/get_template_by_tenant/{tenant_id}")
    async def get_template_by_tenant(self, tenant_id: UUID):
        """Retrieve SMS templates by tenant ID."""
        return await self.sms_template_service.get_templates_by_tenant(tenant_id)
    
    @get("/get_template_by_filter")
    async def get_template_by_filter(self,filters:SMSTemplateFilters):
        """Retrieve SMS templates by filters."""
        return await self.sms_template_service.get_templates_by_filter(filters)