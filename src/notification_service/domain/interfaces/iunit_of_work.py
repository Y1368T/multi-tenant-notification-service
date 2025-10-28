"""
Unit of Work interface.
Manages atomic transactions across multiple repositories.
"""
from abc import ABC, abstractmethod
from typing import Optional

from notification_service.domain.interfaces import *

class IUnitOfWork(ABC):
    """
    Unit of Work interface following the UoW pattern.
    Ensures atomic transactions across multiple repository operations.
    
    Usage example:
        async with uow:
            notification = await uow.notifications.add(notification_entity)
            await uow.delivery_attempts.add(attempt_entity)
            await uow.commit()  # Atomic commit
    """
    
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
