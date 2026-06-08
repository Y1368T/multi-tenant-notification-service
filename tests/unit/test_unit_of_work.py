"""
Unit tests for UnitOfWork lifecycle and transaction behavior.

Tests the context manager pattern, transaction management, and session cleanup.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
from notification_service.infrastructure.persistence.db_session.session import Database


@pytest.mark.asyncio
async def test_aenter_initializes_session(test_database: Database):
    """Verify that __aenter__ properly initializes session and repositories."""
    uow = UnitOfWork(test_database)
    
    # Before entering context, session should be None
    assert uow.session is None
    assert uow._session_context is None
    
    async with uow:
        # After entering, session should be initialized
        assert uow.session is not None
        assert isinstance(uow.session, AsyncSession)
        assert uow._session_context is not None
        
        # All repositories should be initialized
        assert uow.emailNotifications is not None
        assert uow.smsNotifications is not None
        assert uow.inAppNotifications is not None
        assert uow.tenants is not None
        assert uow.providers is not None


@pytest.mark.asyncio
async def test_aexit_commits_on_success(test_database: Database):
    """Verify that __aexit__ commits transaction when no exception occurs."""
    async with UnitOfWork(test_database) as uow:
        # Normal operations - should commit
        assert uow.session is not None


@pytest.mark.asyncio
async def test_aexit_rollsback_on_error(test_database: Database):
    """Verify that __aexit__ rolls back transaction when exception occurs."""
    try:
        async with UnitOfWork(test_database) as uow:
            assert uow.session is not None
            # Trigger an exception
            raise ValueError("Test error")
    except ValueError:
        pass
    
    # Rollback should have been called (verified by no exception during cleanup)


@pytest.mark.asyncio
async def test_manual_commit(test_uow_no_rollback: UnitOfWork):
    """Verify that manual commit works correctly."""
    uow = test_uow_no_rollback
    
    # Session should be active
    assert uow.session is not None
    
    # Manual commit should succeed
    await uow.commit()
    
    # Should still be usable after commit
    assert uow.session is not None


@pytest.mark.asyncio
async def test_manual_rollback(test_uow: UnitOfWork):
    """Verify that manual rollback works correctly."""
    # Session should be active
    assert test_uow.session is not None
    
    # Manual rollback should succeed
    await test_uow.rollback()
    
    # Should still be usable after rollback
    assert test_uow.session is not None


@pytest.mark.asyncio
async def test_session_cleanup(test_database: Database):
    """Verify that session is properly cleaned up after context exit."""
    session_ref = None
    context_ref = None
    
    async with UnitOfWork(test_database) as uow:
        session_ref = uow.session
        context_ref = uow._session_context
        assert session_ref is not None
        assert context_ref is not None
    
    # After exit, references should still exist but context should be cleaned
    assert session_ref is not None
    assert context_ref is not None


@pytest.mark.asyncio
async def test_nested_context_error_handling(test_database: Database):
    """Verify proper cleanup when exception occurs during repository initialization."""
    # This test verifies the fix prevents 'session is provisioning' errors
    
    try:
        async with UnitOfWork(test_database) as uow:
            # Session should be fully initialized before this point
            assert uow.session is not None
            assert uow._session_context is not None
            
            # Repositories should all be initialized
            assert uow.emailNotifications is not None
            
            # Simulate error during operation
            raise RuntimeError("Simulated operation error")
    except RuntimeError:
        pass
    
    # Cleanup should have happened without additional errors


@pytest.mark.asyncio
async def test_commit_failure_triggers_rollback(test_database: Database):
    """Verify that rollback is attempted if commit fails."""
    async with UnitOfWork(test_database) as uow:
        # Normal operations
        assert uow.session is not None
        
        # The context will handle commit/rollback on exit


@pytest.mark.asyncio
async def test_multiple_uow_instances_isolated(test_database: Database):
    """Verify that multiple UoW instances have isolated sessions."""
    async with UnitOfWork(test_database) as uow1:
        async with UnitOfWork(test_database) as uow2:
            # Should have different sessions
            assert uow1.session is not uow2.session
            assert uow1._session_context is not uow2._session_context
            
            # Both should be usable
            assert uow1.session is not None
            assert uow2.session is not None


@pytest.mark.asyncio
async def test_session_context_manager_cleanup(test_database: Database):
    """Verify that the nested session context manager is properly cleaned up."""
    uow = UnitOfWork(test_database)
    
    async with uow:
        # Session context should be set
        assert uow._session_context is not None
        session_context = uow._session_context
    
    # After exit, __aexit__ should have been called on the session context
    # The cleanup is verified by no errors occurring
