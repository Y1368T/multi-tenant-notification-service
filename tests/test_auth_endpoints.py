"""HTTP integration tests for Authentication API endpoints.

Mocking strategy
----------------
The app uses punq as a DI container. ``IKeycloakClient`` is registered as a
**singleton**, and the route handlers are bound to a singleton ``AuthController``
that was resolved (and had ``AuthService`` injected) at ``Builder.build()`` time.

Because the singleton is baked in at build time, the only reliable way to mock
Keycloak is via ``mock.patch.object`` on the **already-instantiated singleton**:

    with patch.object(real_kc, "method", new_callable=AsyncMock) as m:
        ...

This replaces the method on the existing singleton object so every code path
(AuthService, get_user_context, ...) sees the mock.

We build the app and start the TestClient **once per module** (scope="module")
to avoid the asyncpg event-loop-closed errors that occur when the full lifespan
(DB pool, RabbitMQ, OutboxProcessor...) is torn down and restarted between tests.

NullPool fix
---------------------------------
asyncpg's pooled connections raise
"cannot perform operation: another operation is in progress"
when concurrent async tasks share a pooled connection during lifespan startup
(provider seed) and the first request.  Using NullPool gives each session
its own fresh connection with no pool-level concurrency.

OutboxProcessor fix
---------------------------------
The OutboxProcessor background task runs _process_all_outboxes() immediately
on startup (before its first sleep). That concurrent DB session clashes with
the request-level session. We patch it to an async no-op so it never
touches the DB during tests.
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from notification_service.main import main
from notification_service.domain.interfaces.ikeycloak_client import IKeycloakClient
from notification_service.infrastructure.jobs.outbox_processor import OutboxProcessor
from notification_service.infrastructure.persistence.db_session.session import Database
from qena_shared_lib.dependencies.http import get_container


# Patch helpers defined at module level (used inside fixture)

async def _nullpool_connect(self):
    """
    Replacement for Database.connect that uses NullPool.

    NullPool creates a fresh connection per session with no sharing/reuse,
    eliminating asyncpg "another operation is in progress" errors when the
    provider-seed task, OutboxProcessor task, and request handler all run
    concurrently during TestClient lifespan startup.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Initializing database (NullPool / test mode)...")
    self.engine = create_async_engine(
        self.database_url,
        echo=False,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    self.session_maker = async_sessionmaker(
        bind=self.engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with self.engine.begin() as conn:
        await conn.run_sync(lambda _: None)
    logger.info("Database connection established successfully (NullPool).")


async def _noop_process_all_outboxes(self):
    """No-op replacement: prevents OutboxProcessor from doing DB work in tests."""
    pass


# Module-scoped fixtures  — built & started once for the whole test module

@pytest.fixture(scope="module")
def app():
    """
    Build the FastAPI app once per module with:
    - NullPool DB engine  -> no shared asyncpg connections
    - OutboxProcessor._process_all_outboxes -> no-op
    """
    with (
        patch.object(Database, "connect", new=_nullpool_connect),
        patch.object(OutboxProcessor, "_process_all_outboxes", new=_noop_process_all_outboxes),
    ):
        application = main()

    # The `with` exits (restores originals) but the already-built `application`
    # object holds the already-replaced engine+session_maker from _nullpool_connect.
    # The OutboxProcessor instance inside the lifespan also already has the
    # patched class method for the duration of the running event loop.
    return application


@pytest.fixture(scope="module")
def http_client(app):
    """Start the app lifespan once for the whole module."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def real_kc(app):
    """Resolve the IKeycloakClient singleton from the DI container."""
    return get_container(app).resolve(IKeycloakClient)


# Tests

def test_register_endpoint_success(http_client, real_kc):
    unique_email = f"user-{uuid4()}@example.com"
    kc_id = f"kc-reg-{uuid4()}"

    with (
        patch.object(real_kc, "register", new_callable=AsyncMock) as m_register,
        patch.object(real_kc, "login", new_callable=AsyncMock) as m_login,
        patch.object(real_kc, "verifyToken", new_callable=AsyncMock) as m_verify,
    ):
        m_register.return_value = kc_id
        m_login.return_value = {
            "access_token": "access-tok-register",
            "refresh_token": "refresh-tok-register",
            "expires_in": 300,
            "token_type": "Bearer",
        }
        m_verify.return_value = {"sub": kc_id}

        response = http_client.post("/auth/register", json={
            "email": unique_email,
            "password": "SecurePassword123",
            "fullName": "Integration Test User",
            "role": "tenant-manager",
        })

        # Assertions inside `with` so mock call records are still valid
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["accessToken"] == "access-tok-register"
        assert data["refreshToken"] == "refresh-tok-register"
        assert data["sessionToken"] is not None
        assert data["user"]["email"] == unique_email
        assert data["user"]["fullName"] == "Integration Test User"
        assert data["user"]["isActive"] is True
        m_register.assert_called_once()
        m_login.assert_called_once()


def test_register_endpoint_duplicate_email(http_client, real_kc):
    unique_email = f"dup-{uuid4()}@example.com"
    kc_id = f"kc-dup-{uuid4()}"

    with (
        patch.object(real_kc, "register", new_callable=AsyncMock) as m_register,
        patch.object(real_kc, "login", new_callable=AsyncMock) as m_login,
        patch.object(real_kc, "verifyToken", new_callable=AsyncMock),
    ):
        m_register.return_value = kc_id
        m_login.return_value = {
            "access_token": "tok1", "refresh_token": "rtok1",
            "expires_in": 300, "token_type": "Bearer",
        }

        r1 = http_client.post("/auth/register", json={
            "email": unique_email,
            "password": "SecurePassword123",
            "fullName": "Dup User",
            "role": "tenant-manager",
        })
        assert r1.status_code == 201, r1.text

        r2 = http_client.post("/auth/register", json={
            "email": unique_email,
            "password": "SecurePassword123",
            "fullName": "Dup User",
            "role": "tenant-manager",
        })
        assert r2.status_code == 409, r2.text
        assert "already exists" in r2.json()["message"]


def test_login_endpoint_success(http_client, real_kc):
    unique_email = f"login-{uuid4()}@example.com"
    kc_id = f"kc-login-{uuid4()}"

    with (
        patch.object(real_kc, "register", new_callable=AsyncMock) as m_register,
        patch.object(real_kc, "login", new_callable=AsyncMock) as m_login,
        patch.object(real_kc, "verifyToken", new_callable=AsyncMock) as m_verify,
    ):
        # Register first
        m_register.return_value = kc_id
        m_login.return_value = {
            "access_token": "access-reg", "refresh_token": "refresh-reg",
            "expires_in": 3600, "token_type": "Bearer",
        }
        m_verify.return_value = {"sub": kc_id}

        reg = http_client.post("/auth/register", json={
            "email": unique_email, "password": "SecurePassword123",
            "fullName": "Login Tester", "role": "tenant-manager",
        })
        assert reg.status_code == 201, reg.text

        # Now login with fresh tokens
        m_login.return_value = {
            "access_token": "access-login", "refresh_token": "refresh-login",
            "expires_in": 3600, "token_type": "Bearer",
        }
        m_verify.return_value = {"sub": kc_id}

        response = http_client.post("/auth/login", json={
            "email": unique_email, "password": "SecurePassword123",
        })

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["accessToken"] == "access-login"
        assert data["refreshToken"] == "refresh-login"
        assert data["sessionToken"] is not None
        assert data["user"]["email"] == unique_email


def test_login_endpoint_user_not_in_local_db(http_client, real_kc):
    """Keycloak accepts the login, but the user has no local DB record."""
    kc_id = f"kc-unknown-{uuid4()}"

    with (
        patch.object(real_kc, "login", new_callable=AsyncMock) as m_login,
        patch.object(real_kc, "verifyToken", new_callable=AsyncMock) as m_verify,
    ):
        m_login.return_value = {
            "access_token": "access-unknown", "refresh_token": "refresh-unknown",
            "expires_in": 3600, "token_type": "Bearer",
        }
        m_verify.return_value = {"sub": kc_id}

        response = http_client.post("/auth/login", json={
            "email": "ghost@example.com", "password": "SecurePassword123",
        })

        assert response.status_code == 401, response.text
        assert "not found in local database" in response.json()["message"]


def test_logout_endpoint(http_client, real_kc):
    """Logout should revoke the refresh token in Keycloak."""
    with patch.object(real_kc, "logout", new_callable=AsyncMock) as m_logout:
        response = http_client.post("/auth/logout", json={
            "refreshToken": "some-refresh-token-to-revoke",
        })

        assert response.status_code == 200, response.text
        assert response.json()["message"] == "Logged out successfully"
        # auth_service.py calls: await self.keycloakClient.logout(refreshToken) [positional]
        m_logout.assert_called_once_with("some-refresh-token-to-revoke")


def test_refresh_endpoint_success(http_client, real_kc):
    """Refresh should exchange old token for a new token pair."""
    with (
        patch.object(real_kc, "refreshToken", new_callable=AsyncMock) as m_refresh,
        patch.object(real_kc, "verifyToken", new_callable=AsyncMock) as m_verify,
    ):
        m_refresh.return_value = {
            "access_token": "new-access", "refresh_token": "new-refresh",
            "expires_in": 300, "token_type": "Bearer",
        }
        m_verify.return_value = {"sub": "kc-some-user"}

        response = http_client.post("/auth/refresh", json={"refreshToken": "old-refresh-token"})

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["accessToken"] == "new-access"
        assert data["refreshToken"] == "new-refresh"
        # auth_service.py calls: await self.keycloakClient.refreshToken(refreshToken) [positional]
        m_refresh.assert_called_once_with("old-refresh-token")


def test_me_endpoint_success(http_client, real_kc):
    """/me returns the authenticated user's profile using the backend session token."""
    unique_email = f"me-{uuid4()}@example.com"
    kc_id = f"kc-me-{uuid4()}"

    with (
        patch.object(real_kc, "register", new_callable=AsyncMock) as m_register,
        patch.object(real_kc, "login", new_callable=AsyncMock) as m_login,
        patch.object(real_kc, "verifyToken", new_callable=AsyncMock) as m_verify,
    ):
        m_register.return_value = kc_id
        m_login.return_value = {
            "access_token": "access-me", "refresh_token": "refresh-me",
            "expires_in": 3600, "token_type": "Bearer",
        }
        m_verify.return_value = {"sub": kc_id}

        reg = http_client.post("/auth/register", json={
            "email": unique_email, "password": "SecurePassword123",
            "fullName": "Me Tester", "role": "tenant-manager",
        })
        assert reg.status_code == 201, reg.text

        # sessionToken is a signed backend JWT - verified locally, no Keycloak call needed
        session_token = reg.json()["sessionToken"]

    response = http_client.get("/auth/me", headers={"Authorization": f"Bearer {session_token}"})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == unique_email
    assert data["fullName"] == "Me Tester"
    assert data["isActive"] is True


def test_me_endpoint_no_token(http_client):
    """/me should return 401 if no Authorization header is provided."""
    response = http_client.get("/auth/me")
    assert response.status_code == 401, response.text
