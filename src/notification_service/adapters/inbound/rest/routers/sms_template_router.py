from fastapi import Depends
from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest, PaginatedRequestDTO, RelatedFilter
from qena_shared_lib.http import ControllerBase,get,post,api_controller,put,delete
from notification_service.application.services.sms_template_service import SMSTemplateService
from notification_service.adapters.inbound.dto.sms_template_request_dto import SMSTemplateRequestDTO,SMSTemplateFilters
from uuid import UUID

@api_controller(prefix="/sms-templates", tags=["SMS Templates"])
class SMSTemplateController(ControllerBase):
    
    def __init__(self, smsTemplateService: SMSTemplateService):
        self.smsTemplateService = smsTemplateService
    
    @post("/create")
    async def createSmsTemplate(self, template:SMSTemplateRequestDTO):
        """Create a new SMS template."""
        entity=template.toEntity()
        return await self.smsTemplateService.createSmsTemplate(entity)
    
    @get("/get_template_by_tenant/{tenant_id}")
    async def getTemplateByTenant(self, tenant_id: UUID):
        """Retrieve SMS templates by tenant ID."""
        return await self.smsTemplateService.getTemplatesByTenant(tenant_id)
    
    @get("/get_template_by_filter")
    async def getTemplateByFilter(self,params:PaginatedRequestDTO=Depends()):
        """Retrieve SMS templates by filters."""
        defaultSearchFields = [
            "templateName",
            "serviceName",
        ]

        rootFilters = {"tenantId": params.tenantId} if params.tenantId else {}
        relatedFilters: list[RelatedFilter] = []
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
        
        return await self.smsTemplateService.getAllTemplatesAdvanced(req)