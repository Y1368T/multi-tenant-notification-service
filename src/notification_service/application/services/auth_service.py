"""Authentication application service.

Orchestrates all auth flows:
- register: Create user in Keycloak + local DB
- login: Authenticate via Keycloak, return tokens + profile
- logout: Revoke tokens in Keycloak
- refresh: Get new token pair
- getCurrentUser: Look up user by keycloakId, return profile
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.interfaces.ikeycloak_client import IKeycloakClient
from notification_service.domain.entities.user.user import User
from notification_service.domain.entities.user.user_tenant import UserTenant
from notification_service.shared.exceptions.application_exceptions import (
    EntityNotFoundError,
    ConflictError,
    UnauthorizedError,
)
from notification_service.adapters.inbound.dto.auth_dto import (
    AuthResponseDTO,
    TokenResponseDTO,
    UserProfileDTO,
    TenantMembershipDTO,
)

from notification_service.shared.security.token_service import create_backend_session_token

logger = logging.getLogger(__name__)


class AuthService:
    """Application service for user authentication and management."""

    def __init__(self, uow: IUnitOfWork, keycloakClient: IKeycloakClient):
        self.uow = uow
        self.keycloakClient = keycloakClient

    # REGISTER
    async def register(
        self,
        email: str,
        password: str,
        fullName: str,
        tenantId: Optional[UUID] = None,
        role: str = "tenant-manager",
    ) -> AuthResponseDTO:
        """Register a new user:
        1. Create user in Keycloak (Admin API)
        2. Create local User row
        3. Create UserTenant membership if tenantId given
        4. Login via Keycloak to get tokens
        5. Return tokens + profile
        """
        async with self.uow:
            # Check local DB for duplicate email first (fast check)
            existing = await self.uow.users.getByEmail(email)
            if existing:
                raise ConflictError(f"A user with email '{email}' already exists")

            # Split fullName for Keycloak which requires first + last
            name_parts = fullName.strip().split(" ", 1)
            kc_first = name_parts[0]
            kc_last = name_parts[1] if len(name_parts) > 1 else ""

            # Create user in Keycloak — raises ConflictError if duplicate
            keycloakId = await self.keycloakClient.register(
                email=email,
                password=password,
                firstName=kc_first,
                lastName=kc_last,
            )
            logger.info(f"User created in Keycloak: keycloakId={keycloakId}")

            # Persist local user
            newUser = User(
                id=uuid4(),
                keycloakId=keycloakId,
                email=email,
                fullName=fullName.strip(),
                role="super-admin" if role == "super-admin" else "user",
                isActive=True,
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow(),
            )
            createdUser = await self.uow.users.add(newUser)
            logger.info(f"Local user created: id={createdUser.id}")

            # Link to tenant if provided
            memberships: List[UserTenant] = []
            if tenantId is not None:
                membership = UserTenant(
                    userId=createdUser.id,
                    tenantId=tenantId,
                    role=role,
                    isActive=True,
                    joinedAt=datetime.utcnow(),
                )
                createdMembership = await self.uow.userTenants.add(membership)
                memberships.append(createdMembership)

            await self.uow.commit()

        # Login to get tokens from Keycloak
        tokens = await self.keycloakClient.login(email=email, password=password)

        eff_role = "super-admin" if createdUser.role == "super-admin" else "tenant-manager"
        eff_tenant_id = None if eff_role == "super-admin" else (memberships[0].tenantId if memberships else None)
        session_token = create_backend_session_token(
            user_id=createdUser.id,
            email=createdUser.email,
            full_name=createdUser.fullName or fullName,
            role=eff_role,
            tenant_id=eff_tenant_id,
        )

        return AuthResponseDTO(
            accessToken=tokens["access_token"],
            refreshToken=tokens["refresh_token"],
            sessionToken=session_token,
            tokenType=tokens.get("token_type", "Bearer"),
            expiresIn=tokens["expires_in"],
            user=await self._buildUserProfile(createdUser, memberships),
        )

    # LOGIN
    async def login(self, email: str, password: str) -> AuthResponseDTO:
        """Authenticate user and return tokens + profile.
        
        Keycloak validates credentials. We look up (or lazily create)
        the local user record by keycloakId.
        """
        # Keycloak validates credentials and returns tokens
        tokens = await self.keycloakClient.login(email=email, password=password)

        # Decode access token to get keycloakId (sub claim)
        payload = await self.keycloakClient.verifyToken(tokens["access_token"])
        keycloakId: str = payload["sub"]

        async with self.uow:
            user = await self.uow.users.getByKeycloakId(keycloakId)
            if user is None:
                raise UnauthorizedError(
                    "User authenticated with Keycloak but not found in local database. "
                    "Please contact support."
                )
            if not user.isActive:
                raise UnauthorizedError("User account is deactivated")

            memberships = await self.uow.userTenants.getByUserId(user.id)

        eff_role = "super-admin" if user.role == "super-admin" else "tenant-manager"
        eff_tenant_id = None if eff_role == "super-admin" else (memberships[0].tenantId if memberships else None)
        session_token = create_backend_session_token(
            user_id=user.id,
            email=user.email,
            full_name=user.fullName or "",
            role=eff_role,
            tenant_id=eff_tenant_id,
        )

        return AuthResponseDTO(
            accessToken=tokens["access_token"],
            refreshToken=tokens["refresh_token"],
            sessionToken=session_token,
            tokenType=tokens.get("token_type", "Bearer"),
            expiresIn=tokens["expires_in"],
            user=await self._buildUserProfile(user, memberships),
        )

    # LOGOUT
    async def logout(self, refreshToken: str) -> None:
        """Revoke the refresh token in Keycloak.
        
        This invalidates both the refresh token and any derived access tokens
        on the Keycloak side.
        """
        await self.keycloakClient.logout(refreshToken)
        logger.info("User logged out — refresh token revoked in Keycloak")

    # REFRESH TOKEN
    async def refresh(self, refreshToken: str) -> TokenResponseDTO:
        """Exchange a refresh token for new tokens."""
        tokens = await self.keycloakClient.refreshToken(refreshToken)

        session_token = None
        try:
            payload = await self.keycloakClient.verifyToken(tokens["access_token"])
            keycloakId: str = payload.get("sub", "")
            if keycloakId:
                async with self.uow:
                    user = await self.uow.users.getByKeycloakId(keycloakId)
                    if user and user.isActive:
                        memberships = await self.uow.userTenants.getByUserId(user.id)
                        eff_role = "super-admin" if user.role == "super-admin" else "tenant-manager"
                        eff_tenant_id = None if eff_role == "super-admin" else (memberships[0].tenantId if memberships else None)
                        session_token = create_backend_session_token(
                            user_id=user.id,
                            email=user.email,
                            full_name=user.fullName or "",
                            role=eff_role,
                            tenant_id=eff_tenant_id,
                        )
        except Exception as e:
            logger.warning(f"Could not mint backend session token on refresh: {e}")

        return TokenResponseDTO(
            accessToken=tokens["access_token"],
            refreshToken=tokens["refresh_token"],
            sessionToken=session_token,
            tokenType=tokens.get("token_type", "Bearer"),
            expiresIn=tokens["expires_in"],
        )

    # GET CURRENT USER (/me)
    async def getCurrentUser(self, keycloakId: str) -> UserProfileDTO:
        """Return the full profile for an already-authenticated user.
        
        The keycloakId comes from the verified JWT 'sub' claim,
        which is extracted by the auth dependency before this is called.
        """
        async with self.uow:
            user = await self.uow.users.getByKeycloakId(keycloakId)
            if user is None:
                raise EntityNotFoundError("User", keycloakId)
            if not user.isActive:
                raise UnauthorizedError("User account is deactivated")

            memberships = await self.uow.userTenants.getByUserId(user.id)

        return await self._buildUserProfile(user, memberships)

    # PRIVATE HELPERS
    async def _buildUserProfile(
        self,
        user: User,
        memberships: List[UserTenant],
    ) -> UserProfileDTO:
        """Assemble a UserProfileDTO from a User entity and its memberships."""
        tenantList = [
            TenantMembershipDTO(
                tenantId=m.tenantId,
                tenantName=m.tenantName,
                tenantPrefix=m.tenantPrefix,
                role=m.role,
                isActive=m.isActive,
            )
            for m in memberships
        ]
        return UserProfileDTO(
            userId=user.id,
            email=user.email,
            fullName=user.fullName or "",
            isActive=user.isActive,
            tenants=tenantList,
            createdAt=user.createdAt,
        )
