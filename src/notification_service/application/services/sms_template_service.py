from notification_service.adapters.inbound.dto.paginated_request_dto import PaginatedRequest
from notification_service.adapters.inbound.dto.sms_template_request_dto import SMSTemplateResponseDTO
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from uuid import UUID

from notification_service.domain.value_objects.paginated_result import PaginatedResponseDTO
class SMSTemplateService:
    
    def __init__(self,uow:IUnitOfWork):
        self.uow=uow
    
    async def createSmsTemplate(self,template:SmsTemplate):
        """Create a new SMS template.
        
        Args:
            template: SmsTemplate entity to create
            
        Returns:
            Created SmsTemplate entity with generated ID
        """
        async with self.uow:
            createdTemplate = await self.uow.smsTemplates.add(template)
            await self.uow.commit()
            return createdTemplate
        
    async def getSmsTemplateById(self, templateId):
        """Retrieve an SMS template by its ID.
        
        Args:
            templateId: UUID of the SMS template
            
        Returns:
            SmsTemplate entity if found, None otherwise
        """
        async with self.uow:
            template = await self.uow.smsTemplates.getById(templateId)
            return template
    
    async def updateSmsTemplate(self, template):
        """Update an existing SMS template.
        
        Args:
            template: SmsTemplate entity with updated values
            
        Returns:
            Updated SmsTemplate entity
        """
        async with self.uow:
            updatedTemplate = await self.uow.smsTemplates.update(template)
            await self.uow.commit()
            return updatedTemplate
        
    async def deleteSmsTemplate(self, templateId):
        """Delete an SMS template by its ID.
        
        Args:
            templateId: UUID of the SMS template to delete
            
        Returns:
            None
        """
        async with self.uow:
            await self.uow.smsTemplates.delete(templateId)
            await self.uow.commit()
    
    async def listSmsTemplatesByTenant(self, tenantId):
        """List all SMS templates for a given tenant.
        
        Args:
            tenantId: UUID of the tenant
        Returns:
            List of SmsTemplate entities
        """
        async with self.uow:
            templates = await self.uow.smsTemplates.listByTenant(tenantId)
            return templates
    
    async def getTemplateByFilters(self,tenantId:UUID,templateName:str,serviceName:str):
        """ get list of templates by filters"""
        async with self.uow:
            templates=await self.uow.smsTemplates.list(lambda x:x.tenantId==tenantId and x.templateName==templateName and x.serviceName==serviceName)
            return templates
    
    async def getTemplatesByTenant(self, tenantId: UUID):
        """Retrieve SMS templates by tenant ID.
        
        Args:
            tenantId: UUID of the tenant
            
        Returns:
            List of SmsTemplate entities
        """
        async with self.uow:
            templates = await self.uow.smsTemplates.list(lambda x: x.tenantId == tenantId)
            return templates
        
    async def getAllTemplatesAdvanced(
        self,
        req: PaginatedRequest
    ) -> PaginatedResponseDTO[SMSTemplateResponseDTO]:
        """
        SQL-only filtering, deep relationship filtering, sorting and multi-field search.
        """
        async with self.uow:
            
            relatedFiltersTuples = [
            (rf.relationshipPath, rf.field, rf.op.value if hasattr(rf.op, 'value') else str(rf.op), rf.value)
            for rf in (req.relatedFilters or [])
            ]
            result = await self.uow.smsTemplates.listAdvancedPaginated(
                page=req.page,
                pageSize=req.pageSize,
                rootFilters=req.filters or {},
                relatedFilters=relatedFiltersTuples,
                includes=[],
                sortBy=req.sortBy,
                sortDirection=req.sortDirection.value,
                searchText=req.searchText,
                searchFields=req.searchFields or []
            )

            dtoItems = [
                SMSTemplateResponseDTO.fromEntityWithRelations(template)
                for template in result.items
            ]

            return PaginatedResponseDTO(
                items=dtoItems,
                page=result.page,
                pageSize=result.pageSize,
                totalCount=result.totalCount,
                totalPages=result.totalPages,
                hasNext=result.hasNext,
                hasPrevious=result.hasPrevious
            )