"""FastAPI dependency for JWT authentication, user context resolution, and multi-tenant authorization.

Key design note:
    UnitOfWork requires a Database singleton that is registered in the qena_shared_lib DI
    container at startup (builder.with_singleton(Database)).  FastAPI cannot auto-inject that
    non-Pydantic type through Depends(UnitOfWork) directly, so I pull both UnitOfWork and
    KeycloakClient from the app container via ``request.app`` instead.
"""
import logging
from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from qena_shared_lib.dependencies.http import get_service

from notification_service.domain.entities.user.user import User
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.interfaces.ikeycloak_client import IKeycloakClient
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
from notification_service.infrastructure.services.keycloak_client import KeycloakClient
from notification_service.shared.exceptions.application_exceptions import UnauthorizedError
from notification_service.shared.security.token_service import decode_backend_session_token

logger = logging.getLogger(__name__)

# FastAPI will look for "Authorization: Bearer <token>" header
http_bearer = HTTPBearer(auto_error=False)


@dataclass
class UserContext:
    """User security context parsed from backend session token or Keycloak identity."""
    user_id: UUID
    email: str
    full_name: str
    role: str            # "super-admin" | "tenant-manager"
    tenant_id: Optional[UUID]
    user: Optional[User] = None

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super-admin"

    @property
    def is_tenant_manager(self) -> bool:
        return self.role == "tenant-manager"


async def get_user_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> UserContext:
    """Extract and resolve the UserContext from Bearer token.

    Resolution order:
    1. Try to decode as a signed backend session token (fast, no DB hit).
    2. Fallback: verify as a Keycloak access token, then look up the local user.
    """
    token: Optional[str] = credentials.credentials if credentials else None
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise UnauthorizedError("Authorization token is required")

    # Attempt decoding as signed backend session token first (no DB needed)
    try:
        payload = decode_backend_session_token(token)
        user_id = UUID(payload["user_id"])
        tenant_id = UUID(payload["tenant_id"]) if payload.get("tenant_id") else None
        return UserContext(
            user_id=user_id,
            email=payload.get("email", ""),
            full_name=payload.get("full_name", ""),
            role=payload.get("role", "tenant-manager"),
            tenant_id=tenant_id,
        )
    except Exception:
        # Fall back to Keycloak token verification
        pass

    # Fallback: Verify token as Keycloak access token
    keycloak_client: IKeycloakClient = get_service(request.app, IKeycloakClient)
    payload = await keycloak_client.verifyToken(token)
    keycloakId: Optional[str] = payload.get("sub")
    token_email: Optional[str] = payload.get("email")
    if not keycloakId and not token_email:
        raise UnauthorizedError("Token missing identity claims")

    # Build UnitOfWork using the Database singleton from the DI container
    from notification_service.infrastructure.persistence.db_session.session import Database
    database = get_service(request.app, Database)
    uow = UnitOfWork(database=database)

    async with uow:
        user = None
        if keycloakId:
            user = await uow.users.getByKeycloakId(keycloakId)
        if user is None and token_email:
            user = await uow.users.getByEmail(token_email)
        if user is None:
            raise UnauthorizedError("User not found")
        if not user.isActive:
            raise UnauthorizedError("User account is deactivated")

        memberships = await uow.userTenants.getByUserId(user.id)

    eff_role = "super-admin" if user.role == "super-admin" else "tenant-manager"
    eff_tenant_id = None if eff_role == "super-admin" else (memberships[0].tenantId if memberships else None)

    return UserContext(
        user_id=user.id,
        email=user.email,
        full_name=user.fullName or "",
        role=eff_role,
        tenant_id=eff_tenant_id,
        user=user,
    )


async def get_current_user(
    request: Request,
    ctx: UserContext = Depends(get_user_context),
) -> User:
    """Legacy helper returning User domain entity."""
    if ctx.user:
        return ctx.user
    from notification_service.infrastructure.persistence.db_session.session import Database
    database = get_service(request.app, Database)
    uow = UnitOfWork(database=database)
    async with uow:
        user = await uow.users.getById(ctx.user_id)
        if not user:
            raise UnauthorizedError("User not found")
        return user


def require_role(allowed_roles: List[str]):
    """Returns a dependency function enforcing that the user has one of allowed_roles."""
    async def _role_checker(ctx: UserContext = Depends(get_user_context)) -> UserContext:
        if ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: required role in {allowed_roles}, but user is '{ctx.role}'",
            )
        return ctx
    return _role_checker


def enforce_tenant_access(ctx: UserContext, target_tenant_id: Optional[UUID]) -> None:
    """Enforce data isolation: tenant-manager can only access their assigned tenant_id."""
    if ctx.role == "super-admin":
        return
    if target_tenant_id is not None and ctx.tenant_id != target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: cannot access or modify another tenant's data",
        )


async def require_admin(
    ctx: UserContext = Depends(get_user_context),
) -> UserContext:
    """Dependency requiring super-admin role."""
    if not ctx.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: super-admin role required",
        )
    return ctx
