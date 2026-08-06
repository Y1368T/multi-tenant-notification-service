"""HTTP integration tests for RBAC and multi-tenant authorization guards."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from notification_service.main import main
from notification_service.shared.security.token_service import create_backend_session_token

@pytest.fixture
def client():
    app = main()
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
