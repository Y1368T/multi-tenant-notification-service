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

Connection pool fix
---------------------------------
We replace Database.connect with a version that uses pool_size=1 / max_overflow=0.
This gives the AsyncSession one persistent connection to hold for its full
lifetime — including across await points between queries within the same
session context (e.g. between getByEmail and flush in auth_service.register).

NullPool was tried first but is incompatible with AsyncSession: NullPool
closes the connection immediately after each checkin, so when the session tries
to reuse it after an await boundary it finds it gone and raises:
  InvalidRequestError: This session is provisioning a new connection;
  concurrent operations are not permitted

Background-task fixes
---------------------------------
OutboxProcessor._process_all_outboxes and MetricsRollupProcessor.start are
patched to async no-ops so they never open concurrent DB sessions during the
TestClient lifespan, eliminating the original "another operation is in
progress" asyncpg errors that motivated NullPool in the first place.

Singleton / cross-module contamination fix
---------------------------------
qena_shared_lib registers AuthController as a global singleton. When a second
call to main() happens (e.g. test_rbac_endpoints ran first), the controller
still holds the old KeycloakClient and Database from the first app. The
real_kc fixture (autouse=True) re-binds both attributes on every AuthController
instance found in app.routes, and also sets app.dependency_overrides so that
path-based dependencies (get_user_context) also resolve the correct instances.
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from notification_service.main import main
from notification_service.domain.interfaces.ikeycloak_client import IKeycloakClient
from notification_service.infrastructure.jobs.outbox_processor import OutboxProcessor
from notification_service.infrastructure.jobs.metrics_rollup_processor import MetricsRollupProcessor
from notification_service.infrastructure.persistence.db_session.session import Database
from qena_shared_lib.dependencies.http import get_container, get_service


# Patch helpers defined at module level (used inside fixture)

async def _single_conn_connect(self):
    """
    Replacement for Database.connect that uses a single-connection pool.

    pool_size=1 / max_overflow=0 gives AsyncSession one persistent connection
    to hold for its full lifetime, including across await points between
    queries within the same session context. This avoids the
    'session is provisioning a new connection; concurrent operations are not
    permitted' error that NullPool causes (NullPool closes the connection
    immediately after each checkin, so the session can't reuse it after an
    await boundary).

    Background tasks (OutboxProcessor, MetricsRollupProcessor) are separately
    patched to no-ops so they never compete for this single connection slot.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Initializing database (pool_size=1 / test mode)...")
    self.engine = create_async_engine(
        self.database_url,
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
    logger.info("Database connection established successfully (pool_size=1).")


async def _noop_process_all_outboxes(self):
    """No-op replacement: prevents OutboxProcessor from doing DB work in tests."""
    pass


async def _noop_start_metrics(self):
    """No-op replacement: prevents MetricsRollupProcessor from doing DB work in tests."""
    pass


# Module-scoped fixtures  — built & started once for the whole test module

@pytest.fixture(scope="module", autouse=True)
def _setup(request):
    """Master module fixture: build app → rebind singletons → start TestClient.

    Runs in a guaranteed order because everything is in one fixture:
    1. Build the FastAPI app (background tasks patched).
    2. Resolve IKeycloakClient and Database from the container.
    3. Set app.dependency_overrides so path-based deps (get_user_context)
       resolve the correct instances.
    4. Rebind ctrl.authService.keycloakClient / .uow.database on every
       AuthController instance in app.routes, overriding the stale
       singleton references left by any previous call to main().
    5. Start TestClient (which triggers lifespan / DB connect).

    Both the TestClient and the KeycloakClient instance are stashed on the
    module so that the thin http_client / real_kc fixtures can expose them.
    """
    # 1. Build app with background tasks disabled
    with (
        patch.object(OutboxProcessor, "_process_all_outboxes", new=_noop_process_all_outboxes),
        patch.object(MetricsRollupProcessor, "start", new=_noop_start_metrics),
    ):
        app = main()

    # 2. Resolve the active kc / db for THIS app
    kc = get_container(app).resolve(IKeycloakClient)
    db = get_service(app, Database)

    # 3. Override path-based dependencies
    app.dependency_overrides[IKeycloakClient] = lambda: kc
    app.dependency_overrides[Database] = lambda: db

    # 4. Rebind every AuthController singleton's authService to use this app's
    #    kc and db.  This is necessary because qena_shared_lib registers
    #    AuthController as a punq singleton — a second call to main() reuses
    #    the controller instance built by the first call, which still references
    #    the first app's kc and db.
    for route in app.routes:
        if hasattr(route, "endpoint") and hasattr(route.endpoint, "__self__"):
            ctrl = route.endpoint.__self__
            if hasattr(ctrl, "authService"):
                ctrl.authService.keycloakClient = kc
                ctrl.authService.uow.database = db

    # 5. Start TestClient (triggers lifespan — DB pool is created here)
    with (
        patch.object(Database, "connect", new=_single_conn_connect),
        patch.object(OutboxProcessor, "_process_all_outboxes", new=_noop_process_all_outboxes),
        patch.object(MetricsRollupProcessor, "start", new=_noop_start_metrics),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            # Stash on the module so thin fixtures can read them
            request.module._test_client = client
            request.module._test_kc = kc
            yield

    # Cleanup: remove dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def http_client(request):
    """Thin accessor — returns the TestClient started by _setup."""
    return request.module._test_client


@pytest.fixture(scope="module")
def real_kc(request):
    """Thin accessor — returns the KeycloakClient instance used by controllers.

    Tests patch its methods:
        with patch.object(real_kc, "login", new_callable=AsyncMock) as m: ...
    """
    return request.module._test_kc


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
        err_body = r2.json()
        msg = (err_body.get("error", {}) if isinstance(err_body.get("error"), dict) else {}).get("message") or err_body.get("message") or str(err_body.get("error", ""))
        assert "already exists" in msg


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
        err_body = response.json()
        msg = (err_body.get("error", {}) if isinstance(err_body.get("error"), dict) else {}).get("message") or err_body.get("message") or str(err_body.get("error", ""))
        assert "not found in local database" in msg


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
