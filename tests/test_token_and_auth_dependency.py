"""Unit tests for token service and auth dependencies."""
import pytest
from uuid import uuid4
from fastapi import HTTPException

from notification_service.shared.security.token_service import (
    create_backend_session_token,
    decode_backend_session_token,
)
from notification_service.adapters.inbound.rest.dependencies.auth_dependency import (
    UserContext,
    enforce_tenant_access,
    require_role,
)


def test_token_service_encode_decode():
    user_id = uuid4()
    tenant_id = uuid4()
    token = create_backend_session_token(
        user_id=user_id,
        email="tenant@example.com",
        full_name="Tenant Manager",
        role="tenant-manager",
        tenant_id=tenant_id,
    )
    assert isinstance(token, str)

    payload = decode_backend_session_token(token)
    assert payload["user_id"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == "tenant-manager"
    assert payload["email"] == "tenant@example.com"


def test_super_admin_token_null_tenant():
    user_id = uuid4()
    token = create_backend_session_token(
        user_id=user_id,
        email="admin@kifiya.com",
        full_name="Super Admin",
        role="super-admin",
        tenant_id=None,
    )
    payload = decode_backend_session_token(token)
    assert payload["role"] == "super-admin"
    assert payload["tenant_id"] is None


def test_enforce_tenant_access_allows_same_tenant():
    tenant_id = uuid4()
    ctx = UserContext(
        user_id=uuid4(),
        email="manager@example.com",
        full_name="Manager",
        role="tenant-manager",
        tenant_id=tenant_id,
    )
    # Should not raise exception
    enforce_tenant_access(ctx, tenant_id)


def test_enforce_tenant_access_denies_different_tenant():
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    ctx = UserContext(
        user_id=uuid4(),
        email="manager@example.com",
        full_name="Manager",
        role="tenant-manager",
        tenant_id=tenant_id,
    )
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_access(ctx, other_tenant_id)
    assert exc_info.value.status_code == 403


def test_enforce_tenant_access_allows_super_admin_any_tenant():
    other_tenant_id = uuid4()
    ctx = UserContext(
        user_id=uuid4(),
        email="admin@kifiya.com",
        full_name="Super Admin",
        role="super-admin",
        tenant_id=None,
    )
    # Super admin can access any tenant without raising 403
    enforce_tenant_access(ctx, other_tenant_id)
