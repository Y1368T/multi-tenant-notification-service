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
            template = await uow.email_templates.get_by_id(template_id)
            await uow.commit()  # Atomic commit
    """
    
    # Email repositories
    @property
    @abstractmethod
    def email_notifications(self) -> IGenericRepository:
        """Get email notifications repository."""
        pass
    
    @property
    @abstractmethod
    def email_outbox(self) -> IGenericRepository:
        """Get email outbox repository."""
        pass
    
    @property
    @abstractmethod
    def email_templates(self) -> IGenericRepository:
        """Get email templates repository."""
        pass
    
    # SMS repositories
    @property
    @abstractmethod
    def sms_notifications(self) -> IGenericRepository:
        """Get SMS notifications repository."""
        pass
    
    @property
    @abstractmethod
    def sms_outbox(self) -> IGenericRepository:
        """Get SMS outbox repository."""
        pass
    
    @property
    @abstractmethod
    def sms_templates(self) -> IGenericRepository:
        """Get SMS templates repository."""
        pass
    
    # In-app repositories
    @property
    @abstractmethod
    def in_app_notifications(self) -> IGenericRepository:
        """Get in-app notifications repository."""
        pass
    
    @property
    @abstractmethod
    def in_app_templates(self) -> IGenericRepository:
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
    def tenant_email_configurations(self) -> IGenericRepository:
        """Get tenant email configurations repository."""
        pass
    
    @property
    @abstractmethod
    def tenant_sms_configurations(self) -> IGenericRepository:
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
