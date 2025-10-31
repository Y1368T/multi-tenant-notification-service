"""SMS template repository implementation."""
from sqlalchemy.ext.asyncio import AsyncSession
from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.Infrastructure.persisitence.models.sms.sms_template import SmsTemplateModel
from notification_service.domain.entities.sms.sms_template import SmsTemplate
from notification_service.Infrastructure.persisitence.mappers.sms_template_mapper import SmsTemplateMapper

class SmsTemplateRepository(GenericRepository[SmsTemplateModel, SmsTemplate]):
    """Repository for SMS templates."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, SmsTemplateModel, SmsTemplateMapper)
