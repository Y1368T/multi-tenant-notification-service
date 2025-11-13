"""
Unit of Work interface.
Manages atomic transactions across multiple repositories.
"""
from abc import ABC, abstractmethod
from typing import Optional

from notification_service.domain.interfaces.igeneric_repository import IGenericRepository
from notification_service.domain.interfaces.custom_repositories.itenant_repository import ITenantRepository

class IUnitOfWork(ABC):
    """
    Unit of Work interface following the UoW pattern.
    Ensures atomic transactions across multiple repository operations.
    
    Usage example:
        async with uow:
            notification = await uow.email_notifications.add(notification_entity)
            template = await uow.email_templates.getById(template_id)
            await uow.commit()  # Atomic commit
    """
    # ProviderRespositories
    @property
    @abstractmethod
    def providers(self) -> IGenericRepository:
        """Get providers repository."""
        pass

    # Email repositories
    @property
    @abstractmethod
    def emailNotifications(self) -> IGenericRepository:
        """Get email notifications repository."""
        pass
    
    @property
    @abstractmethod
    def emailOutbox(self) -> IGenericRepository:
        """Get email outbox repository."""
        pass
    
    @property
    @abstractmethod
    def emailTemplates(self) -> IGenericRepository:
        """Get email templates repository."""
        pass
    
    # SMS repositories
    @property
    @abstractmethod
    def smsNotifications(self) -> IGenericRepository:
        """Get SMS notifications repository."""
        pass
    
    @property
    @abstractmethod
    def smsOutbox(self) -> IGenericRepository:
        """Get SMS outbox repository."""
        pass
    
    @property
    @abstractmethod
    def smsTemplates(self) -> IGenericRepository:
        """Get SMS templates repository."""
        pass
    
    # In-app repositories
    @property
    @abstractmethod
    def inAppNotifications(self) -> IGenericRepository:
        """Get in-app notifications repository."""
        pass
    
    @property
    @abstractmethod
    def inAppTemplates(self) -> IGenericRepository:
        """Get in-app templates repository."""
        pass
    
    # Tenant repositories
    @property
    @abstractmethod
    def tenants(self) -> ITenantRepository:
        """Get tenants repository."""
        pass
    
    @property
    @abstractmethod
    def tenantEmailConfigurations(self) -> IGenericRepository:
        """Get tenant email configurations repository."""
        pass
    
    @property
    @abstractmethod
    def tenantSmsConfigurations(self) -> IGenericRepository:
        """Get tenant SMS configurations repository."""
        pass
    
    @abstractmethod
    async def __aenter__(self):
        """Enter async context manager."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager and rollback on exception."""
        pass
    
    @abstractmethod
    async def commit(self) -> None:
        """
        Commit all changes in the current transaction.
        Should be called explicitly within the context manager.
        """
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """
        Rollback all changes in the current transaction.
        Called automatically on exception.
        """
        pass
    @abstractmethod 
    async def close(self) -> None:
        """
        Close the unit of work, releasing any resources.
        """
        pass
