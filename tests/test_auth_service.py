"""Unit tests for AuthService using mocked dependencies."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from notification_service.application.services.auth_service import AuthService
from notification_service.domain.entities.user.user import User
from notification_service.domain.entities.user.user_tenant import UserTenant


@pytest.fixture
def mock_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users = AsyncMock()
    uow.userTenants = AsyncMock()
    return uow


@pytest.fixture
def mock_keycloak():
    kc = AsyncMock()
    kc.register = AsyncMock(return_value="kc-id-123")
    kc.login = AsyncMock(return_value={
        "access_token": "access.token.here",
        "refresh_token": "refresh.token.here",
        "expires_in": 300,
        "token_type": "Bearer",
    })
    kc.verifyToken = AsyncMock(return_value={"sub": "kc-id-123", "email": "test@example.com"})
    return kc


@pytest.mark.asyncio
async def test_register_creates_user(mock_uow, mock_keycloak):
    # Arrange
    mock_uow.users.getByEmail = AsyncMock(return_value=None)  # no duplicate
    mock_uow.users.add = AsyncMock(return_value=User(
        id=uuid4(), keycloakId="kc-id-123", email="test@example.com",
        fullName="Test User", createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    ))
    mock_uow.userTenants.add = AsyncMock(return_value=UserTenant(
        userId=uuid4(), tenantId=uuid4(), role="tenant-manager"
    ))

    service = AuthService(uow=mock_uow, keycloakClient=mock_keycloak)

    # Act
    result = await service.register(
        email="test@example.com",
        password="Secure123",
        fullName="Test User",
    )

    # Assert
    assert result.accessToken == "access.token.here"
    assert result.sessionToken is not None
    assert result.user.email == "test@example.com"
    assert result.user.fullName == "Test User"
    mock_keycloak.register.assert_called_once()
    mock_uow.users.add.assert_called_once()


@pytest.mark.asyncio
async def test_login_returns_tokens(mock_uow, mock_keycloak):
    # Arrange
    mock_uow.users.getByKeycloakId = AsyncMock(return_value=User(
        id=uuid4(), keycloakId="kc-id-123", email="test@example.com",
        fullName="Test User", createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    ))
    mock_uow.userTenants.getByUserId = AsyncMock(return_value=[])

    service = AuthService(uow=mock_uow, keycloakClient=mock_keycloak)

    # Act
    result = await service.login(email="test@example.com", password="Secure123")

    # Assert
    assert result.accessToken == "access.token.here"
    assert result.refreshToken == "refresh.token.here"
    assert result.sessionToken is not None
