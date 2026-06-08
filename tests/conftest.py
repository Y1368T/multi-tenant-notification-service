"""
Pytest fixtures for notification service tests.

Provides shared fixtures for database, session, and UnitOfWork testing.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator

from notification_service.config.settings import Settings
from notification_service.infrastructure.persistence.db_session.session import Database, Base
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide test settings with in-memory SQLite database.
    
    Uses SQLite for fast unit tests. Can be overridden for PostgreSQL integration tests.
    """
    settings = Settings()
    # Use in-memory SQLite for unit tests
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    return settings


@pytest_asyncio.fixture
async def test_database(test_settings: Settings) -> AsyncGenerator[Database, None]:
    """Provide a test Database instance with tables created.
    
    Creates all tables before tests and disposes engine after.
    """
    database = Database(test_settings)
    await database.connect()
    
    # Create all tables
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield database
    
    # Cleanup
    await database.disconnect()


@pytest_asyncio.fixture
async def test_session(test_database: Database) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test.
    
    Session is automatically closed after test completes.
    """
    async with test_database.getSession() as session:
        yield session


@pytest_asyncio.fixture
async def test_uow(test_database: Database) -> AsyncGenerator[UnitOfWork, None]:
    """Provide a UnitOfWork instance for testing.
    
    Automatically rolls back after each test to maintain isolation.
    """
    async with UnitOfWork(test_database) as uow:
        yield uow
        # Rollback to ensure test isolation
        await uow.rollback()


@pytest_asyncio.fixture
async def test_uow_no_rollback(test_database: Database) -> AsyncGenerator[UnitOfWork, None]:
    """Provide a UnitOfWork without automatic rollback.
    
    Use this when you need to test commit behavior explicitly.
    """
    async with UnitOfWork(test_database) as uow:
        yield uow


# PostgreSQL fixtures for integration tests

@pytest.fixture(scope="session")
def postgres_test_settings() -> Settings:
    """Provide test settings with PostgreSQL database.
    
    Uses a separate test database for integration tests.
    """
    settings = Settings()
    # Use a test database - should be configured in .env.test
    # Default to local PostgreSQL with test database
    settings.database_url = "postgresql+asyncpg://notification_svc:wbhg05G332X6rmyfhM2Z@localhost:5432/notification_test_db"
    return settings


@pytest_asyncio.fixture
async def postgres_database(postgres_test_settings: Settings) -> AsyncGenerator[Database, None]:
    """Provide a PostgreSQL test Database instance.
    
    For integration tests that need PostgreSQL-specific features.
    """
    database = Database(postgres_test_settings)
    await database.connect()
    
    # Create all tables
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield database
    
    # Cleanup - drop all tables after tests
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await database.disconnect()


@pytest_asyncio.fixture
async def postgres_session(postgres_database: Database) -> AsyncGenerator[AsyncSession, None]:
    """Provide a PostgreSQL session for integration tests."""
    async with postgres_database.getSession() as session:
        yield session


@pytest_asyncio.fixture
async def postgres_uow(postgres_database: Database) -> AsyncGenerator[UnitOfWork, None]:
    """Provide a PostgreSQL UnitOfWork for integration tests."""
    async with UnitOfWork(postgres_database) as uow:
        yield uow
        await uow.rollback()
