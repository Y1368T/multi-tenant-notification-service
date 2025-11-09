from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from uuid import UUID
class SMSTemplateService:
    
    def __init__(self,uow:IUnitOfWork):
        self.uow=uow
    
    async def create_sms_template(self,template:SmsTemplate):
        """Create a new SMS template.
        
        Args:
            template: SmsTemplate entity to create
            
        Returns:
            Created SmsTemplate entity with generated ID
        """
        async with self.uow:
            created_template = await self.uow.sms_templates.add(template)
            await self.uow.commit()
            return created_template
        
    async def get_sms_template_by_id(self, template_id):
        """Retrieve an SMS template by its ID.
        
        Args:
            template_id: UUID of the SMS template
            
        Returns:
            SmsTemplate entity if found, None otherwise
        """
        async with self.uow:
            template = await self.uow.sms_templates.get_by_id(template_id)
            return template
    
    async def update_sms_template(self, template):
        """Update an existing SMS template.
        
        Args:
            template: SmsTemplate entity with updated values
            
        Returns:
            Updated SmsTemplate entity
        """
        async with self.uow:
            updated_template = await self.uow.sms_templates.update(template)
            await self.uow.commit()
            return updated_template
        
    async def delete_sms_template(self, template_id):
        """Delete an SMS template by its ID.
        
        Args:
            template_id: UUID of the SMS template to delete
            
        Returns:
            None
        """
        async with self.uow:
            await self.uow.sms_templates.delete(template_id)
            await self.uow.commit()
    
    async def list_sms_templates_by_tenant(self, tenant_id):
        """List all SMS templates for a given tenant.
        
        Args:
            tenant_id: UUID of the tenant
        Returns:
            List of SmsTemplate entities
        """
        async with self.uow:
            templates = await self.uow.sms_templates.list_by_tenant(tenant_id)
            return templates
    
    async def get_template_by_filters(self,tenant_id:UUID,template_name:str,service_name:str):
        """ get list of templates by filters"""
        async with self.uow:
            templates=await self.uow.sms_templates.list(lambda x:x.tenant_id==tenant_id and x.template_name==template_name and x.service_name==service_name)
            return templates
    
    async def get_templates_by_tenant(self, tenant_id: UUID):
        """Retrieve SMS templates by tenant ID.
        
        Args:
            tenant_id: UUID of the tenant
            
        Returns:
            List of SmsTemplate entities
        """
        async with self.uow:
            templates = await self.uow.sms_templates.list(lambda x: x.tenant_id == tenant_id)
            return templates