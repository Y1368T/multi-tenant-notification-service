import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository

from notification_service.Infrastructure.persisitence.repositories.email_notification_repository import EmailNotificationRepository
from notification_service.Infrastructure.persisitence.repositories.email_outbox_repository import EmailOutboxRepository
from notification_service.Infrastructure.persisitence.repositories.email_template_repository import EmailTemplateRepository
from notification_service.Infrastructure.persisitence.repositories.sms_notification_repository import SmsNotificationRepository
from notification_service.Infrastructure.persisitence.repositories.sms_outbox_repository import SmsOutboxRepository
from notification_service.Infrastructure.persisitence.repositories.sms_template_repository import SmsTemplateRepository
from notification_service.Infrastructure.persisitence.repositories.in_app_notification_repository import InAppNotificationRepository
from notification_service.Infrastructure.persisitence.repositories.in_app_template_repository import InAppTemplateRepository
from notification_service.Infrastructure.persisitence.repositories.tenant_repository import TenantRepository
from notification_service.Infrastructure.persisitence.repositories.tenant_email_configuration_repository import TenantEmailConfigurationRepository
from notification_service.Infrastructure.persisitence.repositories.tenant_sms_configuration_repository import TenantSmsConfigurationRepository
from notification_service.Infrastructure.persisitence.mappers.tenant_mapper import TenantMapper
from notification_service.Infrastructure.persisitence.mappers.email_notification_mapper import EmailNotificationMapper
from notification_service.Infrastructure.persisitence.mappers.email_outbox_mapper import EmailOutboxMapper
from notification_service.Infrastructure.persisitence.mappers.email_template_mapper import EmailTemplateMapper
from notification_service.Infrastructure.persisitence.mappers.sms_notification_mapper import SmsNotificationMapper
from notification_service.Infrastructure.persisitence.mappers.sms_outbox_mapper import SmsOutboxMapper
from notification_service.Infrastructure.persisitence.mappers.sms_template_mapper import SmsTemplateMapper
from notification_service.Infrastructure.persisitence.mappers.in_app_notification_mapper import InAppNotificationMapper
from notification_service.Infrastructure.persisitence.mappers.in_app_template_mapper import InAppTemplateMapper
from notification_service.Infrastructure.persisitence.mappers.tenant_email_configuration_mapper import TenantEmailConfigurationMapper
from notification_service.Infrastructure.persisitence.mappers.tenant_sms_configuration_mapper import TenantSmsConfigurationMapper
from notification_service.Infrastructure.persisitence.db_session.session import  Database
logger = logging.getLogger(__name__)


class UnitOfWork(IUnitOfWork):
    """Async Unit of Work managing transactional consistency across repositories."""

    def __init__(self,database: Database):
        self.database=database
        pass
    
    def set_constructor(self):
        self.session = self.database.get_session()
        self._email_notifications = EmailNotificationRepository(self.session)
        self._email_outbox = EmailOutboxRepository(self.session)
        self._email_templates = EmailTemplateRepository(self.session)

        self._sms_notifications = SmsNotificationRepository(self.session)
        self._sms_outbox = SmsOutboxRepository(self.session)
        self._sms_templates = SmsTemplateRepository(self.session)

        self._in_app_notifications = InAppNotificationRepository(self.session)
        self._in_app_templates = InAppTemplateRepository(self.session)

        self._tenants = TenantRepository(self.session, TenantMapper())
        self._tenant_email_configurations = TenantEmailConfigurationRepository(self.session)
        self._tenant_sms_configurations = TenantSmsConfigurationRepository(self.session)

    @property
    def email_notifications(self):
        return self._email_notifications

    @property
    def email_outbox(self):
        return self._email_outbox

    @property
    def email_templates(self):
        return self._email_templates

    @property
    def sms_notifications(self):
        return self._sms_notifications

    @property
    def sms_outbox(self):
        return self._sms_outbox

    @property
    def sms_templates(self):
        return self._sms_templates

    @property
    def in_app_notifications(self):
        return self._in_app_notifications

    @property
    def in_app_templates(self):
        return self._in_app_templates

    @property
    def tenants(self):
        return self._tenants

    @property
    def tenant_email_configurations(self):
        return self._tenant_email_configurations

    @property
    def tenant_sms_configurations(self):
        return self._tenant_sms_configurations

    async def __aenter__(self):
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager; rollback on error, close session."""
        try:
            if exc_type:
                await self.rollback()
            else:
                await self.commit()
        finally:
            await self.close()
        # Re-raise exceptions so upper layers can handle them
        if exc_type:
            raise exc_val

    async def commit(self) -> None:
        """Commit transaction."""
        try:
            await self.session.commit()
            logger.debug("Transaction committed successfully.")
        except Exception as e:
            logger.exception("Error during commit, performing rollback.")
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """Rollback transaction."""
        try:
            await self.session.rollback()
            logger.debug("Transaction rolled back.")
        except Exception as e:
            logger.exception("Error during rollback.")
            raise

    async def close(self) -> None:
        """Close session."""
        try:
            await self.session.close()
            logger.debug("Session closed.")
        except Exception as e:
            logger.exception("Error closing session.")
            raise
