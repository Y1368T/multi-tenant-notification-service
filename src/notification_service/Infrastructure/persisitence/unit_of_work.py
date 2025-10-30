from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.interfaces import IGenericRepository
from notification_service.Infrastructure.persisitence.repositories.generic_repository import GenericRepository
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository
from notification_service.Infrastructure.persisitence.repositories.tenant_repository import TenantRepository
class UnitOfWork(IUnitOfWork):
    async def __aenter__(self):
        # Initialize resources, e.g., database session
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources
        pass

    async def commit(self):
        # Commit transaction
        pass

    @property
    def email_notifications(self) -> IGenericRepository:
        # Return email notifications repository
        if not hasattr(self, '_email_notifications'):
            self._email_notifications = GenericRepository()
        return self._email_notifications

    @property
    def email_outbox(self) -> IGenericRepository:
        # Return email outbox repository
        if not hasattr(self, '_email_outbox'):
            self._email_outbox = GenericRepository()
        return self._email_outbox

    @property
    def email_templates(self) -> IGenericRepository:
        # Return email templates repository
        if not hasattr(self, '_email_templates'):
            self._email_templates = GenericRepository()
        return self._email_templates

    @property
    def sms_notifications(self) -> IGenericRepository:
        # Return SMS notifications repository
        if not hasattr(self, '_sms_notifications'):
            self._sms_notifications = GenericRepository()
        return self._sms_notifications

    @property
    def sms_outbox(self) -> IGenericRepository:
        # Return SMS outbox repository
        if not hasattr(self, '_sms_outbox'):
            self._sms_outbox = GenericRepository()
        return self._sms_outbox

    @property
    def sms_templates(self) -> IGenericRepository:
        # Return SMS templates repository
        if not hasattr(self, '_sms_templates'):
            self._sms_templates = GenericRepository()
        return self._sms_templates

    @property
    def in_app_notifications(self) -> IGenericRepository:
        # Return in-app notifications repository
        if not hasattr(self, '_in_app_notifications'):
            self._in_app_notifications = GenericRepository()
        return self._in_app_notifications

    @property
    def in_app_templates(self) -> IGenericRepository:
        # Return in-app templates repository
        if not hasattr(self, '_in_app_templates'):
            self._in_app_templates = GenericRepository()
        return self._in_app_templates

    @property
    def tenants(self) -> ITenantRepository:
        # Return tenants repository
        if not hasattr(self, '_tenants'):
            self._tenants = TenantRepository()
        return self._tenants

    @property
    def tenant_email_configurations(self) -> IGenericRepository:
        # Return tenant email configurations repository
        if not hasattr(self, '_tenant_email_configurations'):
            self._tenant_email_configurations = GenericRepository()
        return self._tenant_email_configurations

    @property
    def tenant_sms_configurations(self) -> IGenericRepository:
        # Return tenant SMS configurations repository
        if not hasattr(self, '_tenant_sms_configurations'):
            self._tenant_sms_configurations = GenericRepository()
        return self._tenant_sms_configurations