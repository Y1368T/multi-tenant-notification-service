import logging
from typing import Optional
from notification_service.infrastructure.persistence.repositories.tenant_inapp_configuration_repository import TenantInAppConfigurationRepository
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository

from notification_service.infrastructure.persistence.repositories.email_notification_repository import EmailNotificationRepository
from notification_service.infrastructure.persistence.repositories.email_outbox_repository import EmailOutboxRepository
from notification_service.infrastructure.persistence.repositories.email_template_repository import EmailTemplateRepository
from notification_service.infrastructure.persistence.repositories.sms_notification_repository import SmsNotificationRepository
from notification_service.infrastructure.persistence.repositories.sms_outbox_repository import SmsOutboxRepository
from notification_service.infrastructure.persistence.repositories.sms_template_repository import SmsTemplateRepository
from notification_service.infrastructure.persistence.repositories.in_app_notification_repository import InAppNotificationRepository
from notification_service.infrastructure.persistence.repositories.in_app_template_repository import InAppTemplateRepository
from notification_service.infrastructure.persistence.repositories.in_app_outbox_repository import InAppOutboxRepository
from notification_service.infrastructure.persistence.repositories.tenant_repository import TenantRepository
from notification_service.infrastructure.persistence.repositories.tenant_email_configuration_repository import TenantEmailConfigurationRepository
from notification_service.infrastructure.persistence.repositories.tenant_sms_configuration_repository import TenantSmsConfigurationRepository
from notification_service.infrastructure.persistence.repositories.telegram_notification_repository import TelegramNotificationRepository
from notification_service.infrastructure.persistence.repositories.telegram_outbox_repository import TelegramOutboxRepository
from notification_service.infrastructure.persistence.repositories.telegram_template_repository import TelegramTemplateRepository
from notification_service.infrastructure.persistence.repositories.tenant_telegram_configuration_repository import TenantTelegramConfigurationRepository
from notification_service.infrastructure.persistence.mappers.tenant_mapper import TenantMapper
from notification_service.infrastructure.persistence.db_session.session import  Database
from notification_service.infrastructure.persistence.repositories.provider_repository import ProviderRepository
from notification_service.domain.entities.providers_supported import Provider
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel
from notification_service.infrastructure.persistence.mappers.provider_mapper import ProviderMapper
from notification_service.infrastructure.persistence.repositories.user_repository import UserRepository
from notification_service.infrastructure.persistence.repositories.user_tenant_repository import UserTenantRepository
from notification_service.infrastructure.persistence.mappers.user_mapper import UserMapper

logger = logging.getLogger(__name__)


class UnitOfWork(IUnitOfWork):
    """Async Unit of Work managing transactional consistency across repositories."""

    def __init__(self,database: Database):
        self.database=database
        self.session = None
        self._session_context = None
    
    @property
    def providers(self):
        return self._providers

    @property
    def emailNotifications(self):
        return self._emailNotifications

    @property
    def emailOutbox(self):
        return self._emailOutbox

    @property
    def emailTemplates(self):
        return self._emailTemplates

    @property
    def smsNotifications(self):
        return self._smsNotifications

    @property
    def smsOutboxes(self):
        return self._smsOutboxes
    
    @property
    def inAppOutboxes(self):
        return self._inAppOutboxes

    @property
    def smsTemplates(self):
        return self._smsTemplates

    @property
    def inAppNotifications(self):
        return self._inAppNotifications

    @property
    def inAppTemplates(self):
        return self._inAppTemplates

    @property
    def tenants(self):
        return self._tenants

    @property
    def tenantEmailConfigurations(self):
        return self._tenantEmailConfigurations

    @property
    def tenantSmsConfigurations(self):
        return self._tenantSmsConfigurations

    @property
    def tenantInAppConfigurations(self):
        return self._tenantInAppConfigurations

    @property
    def telegramNotifications(self):
        return self._telegramNotifications

    @property
    def telegramOutboxes(self):
        return self._telegramOutboxes

    @property
    def telegramTemplates(self):
        return self._telegramTemplates

    @property
    def tenantTelegramConfigurations(self):
        return self._tenantTelegramConfigurations

    @property
    def users(self):
        return self._users

    @property
    def userTenants(self):
        return self._userTenants

    async def __aenter__(self):
        """Enter async context manager.
        
        Properly initializes the database session using nested async context manager
        to ensure the connection is fully established before repositories use it.
        This prevents 'session is provisioning a new connection' race conditions.
        """
        # Store the session context manager for proper cleanup in __aexit__
        self._session_context = self.database.getSession()
        # Await the session initialization to ensure connection is established
        self.session = await self._session_context.__aenter__()
        
        # Initialize all repositories with the properly connected session
        self._emailNotifications = EmailNotificationRepository(self.session)
        self._emailOutbox = EmailOutboxRepository(self.session)
        self._emailTemplates = EmailTemplateRepository(self.session)

        self._smsNotifications = SmsNotificationRepository(self.session)
        self._smsOutboxes = SmsOutboxRepository(self.session)
        self._smsTemplates = SmsTemplateRepository(self.session)

        self._inAppNotifications = InAppNotificationRepository(self.session)
        self._inAppTemplates = InAppTemplateRepository(self.session)
        self._inAppOutboxes = InAppOutboxRepository(self.session)

        self._tenants = TenantRepository(self.session, TenantMapper())
        self._tenantEmailConfigurations = TenantEmailConfigurationRepository(self.session)
        self._tenantSmsConfigurations = TenantSmsConfigurationRepository(self.session)
        # TODO: Create TenantInAppConfigurationRepository, Model, and Mapper
        # For now, using SMS configuration repository as placeholder - needs to be replaced
        self._tenantInAppConfigurations = TenantInAppConfigurationRepository(self.session)
        self._telegramNotifications = TelegramNotificationRepository(self.session)
        self._telegramOutboxes = TelegramOutboxRepository(self.session)
        self._telegramTemplates = TelegramTemplateRepository(self.session)
        self._tenantTelegramConfigurations = TenantTelegramConfigurationRepository(self.session)
        self._providers = ProviderRepository(self.session)
        self._users = UserRepository(self.session, UserMapper())
        self._userTenants = UserTenantRepository(self.session)
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager; rollback on error, close session.
        
        Properly cleans up both the session and the nested session context manager.
        """
        try:
            if exc_type:
                await self.rollback()
            else:
                await self.commit()
        except Exception:
            logger.exception("Error during commit or rollback.")
            if not exc_type:
                # commit() raised; attempt a rollback to release any pending transaction
                try:
                    await self.rollback()
                except Exception:
                    logger.exception("Rollback failed after commit error.")
        finally:
            # Clean up the session context manager
            if self._session_context:
                try:
                    await self._session_context.__aexit__(None, None, None)
                    logger.debug("Session context cleaned up.")
                except Exception:
                    logger.exception("Error cleaning up session context.")
        # Re-raise exceptions so upper layers can handle them
        if exc_type:
            raise exc_val

    async def commit(self) -> None:
        """Commit transaction."""
        try:
            await self.session.commit()
            logger.debug("Transaction committed successfully.")
        except Exception as e:
            logger.exception("Error during commit.")
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
