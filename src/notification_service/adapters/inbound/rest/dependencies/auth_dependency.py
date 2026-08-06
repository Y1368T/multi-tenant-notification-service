"""FastAPI dependency for JWT authentication, user context resolution, and multi-tenant authorization."""
import logging
from dataclasses import dataclass
from typing import Optional, List, Callable
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from notification_service.domain.entities.user.user import User
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.interfaces.ikeycloak_client import IKeycloakClient
from notification_service.infrastructure.persistence.unit_of_work import UnitOfWork
from notification_service.infrastructure.services.keycloak_client import KeycloakClient
from notification_service.shared.exceptions.application_exceptions import UnauthorizedError
from notification_service.shared.security.token_service import decode_backend_session_token

logger = logging.getLogger(__name__)

# FastAPI will look for "Authorization: Bearer <token>" header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


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
    token: str = Depends(oauth2_scheme),
    uow: IUnitOfWork = Depends(UnitOfWork),
    keycloakClient: IKeycloakClient = Depends(KeycloakClient),
) -> UserContext:
    """Extract and resolve the UserContext from Bearer token."""
    if not token:
        raise UnauthorizedError("Authorization token is required")

    # 1. Attempt decoding as signed backend session token first
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

    # 2. Fallback: Verify token as Keycloak JWT token
    payload = await keycloakClient.verifyToken(token)
    keycloakId: str = payload.get("sub")
    if not keycloakId:
        raise UnauthorizedError("Token missing 'sub' claim")

    async with uow:
        user = await uow.users.getByKeycloakId(keycloakId)
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
        full_name=f"{user.firstName} {user.lastName}",
        role=eff_role,
        tenant_id=eff_tenant_id,
        user=user,
    )


async def get_current_user(
    ctx: UserContext = Depends(get_user_context),
    uow: IUnitOfWork = Depends(UnitOfWork),
) -> User:
    """Legacy helper returning User domain entity."""
    if ctx.user:
        return ctx.user
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
    """Dependency requiring super-admin or admin role."""
    if not ctx.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: super-admin role required",
        )
    return ctx
