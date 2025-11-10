from fastapi import Depends
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, PaginatedRequestDTO, RelatedFilter
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
    async def get_template_by_filter(self,params:PaginatedRequestDTO=Depends()):
        """Retrieve SMS templates by filters."""
        default_search_fields = [
            "template_name",
            "service_name",
        ]

        root_filters = {"tenant_id": params.tenant_id} if params.tenant_id else {}
        related_filters: list[RelatedFilter] = []
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
        
        return await self.sms_template_service.get_all_templates_advanced(req)