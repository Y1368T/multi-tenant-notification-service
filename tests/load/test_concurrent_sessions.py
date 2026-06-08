"""
Load tests for concurrent database session usage.

These tests verify that the fix prevents the 'session is provisioning a new connection'
race condition that occurs under high concurrency.
"""
import pytest
import pytest_asyncio
import asyncio
from typing import List
from sqlalchemy import text

from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
from notification_service.infrastructure.persistence.db_session.session import Database


@pytest.mark.asyncio
async def test_high_concurrency_sessions(test_database: Database):
    """Test 50+ concurrent sessions to verify no race conditions.
    
    This directly tests the scenario that caused the original error:
    'This session is provisioning a new connection; concurrent operations are not permitted'
    """
    success_count = 0
    errors: List[Exception] = []
    
    async def create_session_and_query():
        nonlocal success_count
        try:
            async with test_database.getSession() as session:
                # Perform a simple query to verify session is usable
                result = await session.execute(text("SELECT 1 as value"))
                row = result.fetchone()
                assert row is not None
                success_count += 1
                return True
        except Exception as e:
            errors.append(e)
            return False
    
    # Create 50 concurrent session operations
    tasks = [create_session_and_query() for _ in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All operations should succeed
    assert success_count == 50, f"Only {success_count}/50 succeeded. Errors: {errors}"
    assert len(errors) == 0, f"Unexpected errors: {errors}"
    assert all(r is True for r in results if not isinstance(r, Exception))


@pytest.mark.asyncio
async def test_connection_pool_behavior(test_database: Database):
    """Verify that session creation respects pool limits without errors."""
    active_sessions = []
    
    async def hold_session_briefly():
        async with test_database.getSession() as session:
            active_sessions.append(session)
            await asyncio.sleep(0.01)  # Brief hold
            result = await session.execute(text("SELECT 1"))
            return result is not None
    
    # Create more concurrent sessions than typical pool size
    tasks = [hold_session_briefly() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    
    # All should succeed without pool exhaustion or race conditions
    assert all(results)
    assert len(results) == 20


@pytest.mark.asyncio
async def test_no_race_conditions_unitofwork(test_database: Database):
    """Verify concurrent UnitOfWork usage is safe.
    
    This tests the real-world scenario where multiple API requests
    create UnitOfWork instances simultaneously.
    """
    success_count = 0
    errors: List[str] = []
    
    async def use_unitofwork():
        nonlocal success_count
        try:
            async with UnitOfWork(test_database) as uow:
                # Verify session is fully initialized
                assert uow.session is not None
                
                # Verify repositories are accessible
                assert uow.emailNotifications is not None
                assert uow.smsNotifications is not None
                
                # Perform a query through the session
                result = await uow.session.execute(text("SELECT 1"))
                assert result is not None
                
                success_count += 1
                return True
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            errors.append(error_msg)
            # Check for the specific error we're trying to prevent
            if "provisioning a new connection" in str(e):
                raise AssertionError(f"Race condition detected: {e}")
            return False
    
    # Simulate 30 concurrent API requests
    tasks = [use_unitofwork() for _ in range(30)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All should succeed
    assert success_count == 30, f"Only {success_count}/30 succeeded. Errors: {errors}"
    assert len(errors) == 0, f"Unexpected errors: {errors}"
    
    # Verify no race condition errors
    for result in results:
        if isinstance(result, Exception):
            assert "provisioning a new connection" not in str(result), \
                "Original race condition still occurring!"


@pytest.mark.asyncio
async def test_session_provisioning_race_original_scenario(test_database: Database):
    """Test the exact scenario from the original error.
    
    Original error:
    'This session is provisioning a new connection; concurrent operations are not permitted'
    
    This occurred when multiple requests hit the service simultaneously and tried
    to use sessions that were still being initialized.
    """
    errors_detected = []
    
    async def simulate_api_request():
        try:
            # Simulate what happens in a typical service method
            async with UnitOfWork(test_database) as uow:
                # Immediately try to access repositories and query
                # (This is where the race condition would occur)
                tenant_repo = uow.tenants
                
                # Try to perform a query that would fail if session not ready
                result = await uow.session.execute(text("SELECT 1"))
                
                return True
        except Exception as e:
            error_msg = str(e)
            if "provisioning a new connection" in error_msg.lower() or \
               "concurrent operations are not permitted" in error_msg.lower():
                errors_detected.append(error_msg)
            raise
    
    # Launch many requests simultaneously (like production traffic spike)
    tasks = [simulate_api_request() for _ in range(40)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check for any race condition errors
    assert len(errors_detected) == 0, \
        f"Race condition detected! Original error still occurring: {errors_detected}"
    
    # All requests should succeed
    successful = sum(1 for r in results if r is True)
    assert successful == 40, f"Only {successful}/40 requests succeeded"


@pytest.mark.asyncio
async def test_rapid_session_create_destroy(test_database: Database):
    """Test rapid creation and destruction of sessions."""
    iterations = 100
    
    async def rapid_session_cycle():
        for _ in range(5):
            async with test_database.getSession() as session:
                await session.execute(text("SELECT 1"))
    
    # Run multiple rapid cycles concurrently
    tasks = [rapid_session_cycle() for _ in range(20)]
    await asyncio.gather(*tasks)
    
    # If we reach here without errors, the test passed


@pytest.mark.asyncio
async def test_concurrent_transactions(test_database: Database):
    """Test concurrent transactions don't interfere with each other."""
    results = []
    
    async def perform_transaction(value: int):
        async with UnitOfWork(test_database) as uow:
            # Each transaction should be isolated
            result = await uow.session.execute(text(f"SELECT {value} as val"))
            row = result.fetchone()
            results.append(row[0] if row else None)
            
            # Commit explicitly
            await uow.commit()
            return value
    
    # Run 25 concurrent transactions
    tasks = [perform_transaction(i) for i in range(25)]
    await asyncio.gather(*tasks)
    
    # All transactions should have completed
    assert len(results) == 25
    # Results should contain all values (order may vary)
    assert set(results) == set(range(25))
