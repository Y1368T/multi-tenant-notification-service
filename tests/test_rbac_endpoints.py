"""HTTP integration tests for RBAC and multi-tenant authorization guards."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from notification_service.main import main
from notification_service.shared.security.token_service import create_backend_session_token

from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.cache.redis_cache import RedisCache
from notification_service.infrastructure.jobs.outbox_processor import OutboxProcessor
from notification_service.infrastructure.jobs.periodic_rollup_worker import PeriodicRollupWorker
from notification_service.infrastructure.messaging.rabbitmq import RabbitMQRPCClient
from notification_service.adapters.inbound.rabbitmq.rabbitmq_consumer import NotificationRabbitMQConsumer


async def _single_conn_connect(self):
    """Replace Database.connect with pool_size=1 for tests.

    Keeps one persistent connection so AsyncSession can hold it across await
    points within a single session context (NullPool closes connections
    immediately after checkin, which breaks the session lifecycle).
    """
    db_url = self.database_url.replace("postgres:5439", "localhost:5437")
    self.engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    self.session_maker = async_sessionmaker(
        bind=self.engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def _noop_process_all_outboxes(self):
    """Prevent OutboxProcessor from touching the DB during tests."""
    pass


async def _noop_start_metrics(self):
    """Prevent PeriodicRollupWorker from touching the DB during tests."""
    pass


@pytest.fixture(scope="module")
def client():
    with (
        patch.object(OutboxProcessor, "_process_all_outboxes", new=_noop_process_all_outboxes),
        patch.object(PeriodicRollupWorker, "start", new=_noop_start_metrics),
        patch.object(RedisCache, "connect", new=AsyncMock()),
        patch.object(RedisCache, "disconnect", new=AsyncMock()),
    ):
        app = main()
    with (
        patch.object(Database, "connect", new=AsyncMock()),
        patch.object(Database, "disconnect", new=AsyncMock()),
        patch("notification_service.main.seed_providers", new=AsyncMock()),
        patch.object(RabbitMQRPCClient, "connect", new=AsyncMock()),
        patch.object(RabbitMQRPCClient, "disconnect", new=AsyncMock()),
        patch.object(NotificationRabbitMQConsumer, "startConsuming", new=AsyncMock()),
        patch.object(NotificationRabbitMQConsumer, "stopConsuming", new=AsyncMock()),
        patch.object(OutboxProcessor, "_process_all_outboxes", new=_noop_process_all_outboxes),
        patch.object(PeriodicRollupWorker, "start", new=_noop_start_metrics),
        patch.object(RedisCache, "connect", new=AsyncMock()),
        patch.object(RedisCache, "disconnect", new=AsyncMock()),
    ):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

def test_tenant_email_config_unauthenticated_returns_401(client):
    response = client.get("/tenant-email-configurations/get")
    assert response.status_code == 401

def test_tenant_email_config_tenant_manager_returns_403(client):
    tenant_manager_token = create_backend_session_token(
        user_id=uuid4(),
        email="manager@tenant1.com",
        full_name="Tenant Manager",
        role="tenant-manager",
        tenant_id=uuid4(),
    )
    headers = {"Authorization": f"Bearer {tenant_manager_token}"}
    response = client.get("/tenant-email-configurations/get", headers=headers)
    assert response.status_code == 403

def test_provider_supported_tenant_manager_returns_403(client):
    tenant_manager_token = create_backend_session_token(
        user_id=uuid4(),
        email="manager@tenant1.com",
        full_name="Tenant Manager",
        role="tenant-manager",
        tenant_id=uuid4(),
    )
    headers = {"Authorization": f"Bearer {tenant_manager_token}"}
    response = client.get("/provider-supported/get", headers=headers)
    assert response.status_code == 403

def test_regenerate_api_key_cross_tenant_returns_403(client):
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()

    token_tenant_a = create_backend_session_token(
        user_id=uuid4(),
        email="manager@tenant1.com",
        full_name="Tenant Manager A",
        role="tenant-manager",
        tenant_id=tenant_a_id,
    )
    headers = {"Authorization": f"Bearer {token_tenant_a}"}
    # Manager from Tenant A trying to regenerate API key for Tenant B
    response = client.post(f"/tenants/{tenant_b_id}/regenerate-api-key", headers=headers)
    assert response.status_code == 403
