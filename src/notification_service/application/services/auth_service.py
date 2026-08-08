import logging
from typing import Optional, Dict, Any, Tuple
import httpx
from datetime import datetime, timedelta, timezone
from jose import jwt

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from notification_service.config.settings import settings
from notification_service.infrastructure.persistence.models.user.user import UserModel
from notification_service.infrastructure.persistence.models.user.user_tenant import UserTenantModel
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.shared.exceptions.application_exceptions import UnauthorizedError

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    async def _keycloak_login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user against Keycloak using ROPC."""
        if settings.mock_keycloak:
            logger.info("Mocking Keycloak authentication for development.")
            return {
                "access_token": "mocked_access_token",
                "refresh_token": "mocked_refresh_token",
                "expires_in": 300,
                "token_type": "Bearer"
            }

        url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
        payload = {
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
            "grant_type": "password",
            "username": email,
            "password": password,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=payload, headers=headers)
                if response.status_code != 200:
                    logger.error(f"Keycloak login failed: {response.text}")
                    raise UnauthorizedError("Invalid email or password.")
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Error connecting to Keycloak: {e}")
                raise UnauthorizedError("Authentication service unavailable.")

    def _generate_mtns_session(self, user: UserModel, tenant_membership: Optional[UserTenantModel]) -> str:
        """Generate a signed JWT session token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(seconds=settings.session_ttl_seconds)

        # Determine effective role and tenant
        # If user is super-admin at global level, keep it. Otherwise check tenant role.
        effective_role = user.role
        tenant_id = None
        tenant_name = None

        if effective_role != "super-admin" and tenant_membership:
            effective_role = tenant_membership.role
            tenant_id = str(tenant_membership.tenant_id)
            tenant_name = tenant_membership.tenant.name if tenant_membership.tenant else None

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": effective_role,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "exp": expire.timestamp(),
            "iat": now.timestamp()
        }

        # Create JWT using jose
        token = jwt.encode(payload, settings.session_signing_key, algorithm="HS256")
        return token

    async def authenticate_user(self, email: str, password: str) -> Tuple[str, Dict[str, Any]]:
        """
        Authenticate user and return the session JWT and user profile.
        
        Returns:
            Tuple[str, Dict[str, Any]]: (mtns_session_jwt, user_profile)
        """
        # 1. Validate credentials with Keycloak
        token_response = await self._keycloak_login(email, password)
        
        # 2. Lookup user in local database
        async with self.uow:
            # We access the raw session since user repository isn't exposed in IUnitOfWork
            session = self.uow.session
            
            # Fetch user with their tenant memberships and tenant details
            stmt = select(UserModel).options(
                selectinload(UserModel.tenantMemberships).selectinload(UserTenantModel.tenant)
            ).where(UserModel.email == email)
            
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user or not user.isActive:
                raise UnauthorizedError("User is deactivated or not found locally.")

            # Identify primary tenant membership if not super-admin
            tenant_membership = None
            if user.role != "super-admin" and user.tenantMemberships:
                # For this implementation, pick the first active membership
                for membership in user.tenantMemberships:
                    if membership.isActive:
                        tenant_membership = membership
                        break
                
                if not tenant_membership:
                    raise UnauthorizedError("User has no active tenant memberships.")

            # 3. Generate internal JWT session
            mtns_session = self._generate_mtns_session(user, tenant_membership)

            # 4. Prepare user profile response
            effective_role = user.role
            tenant_id = None
            tenant_name = None

            if effective_role != "super-admin" and tenant_membership:
                effective_role = tenant_membership.role
                tenant_id = str(tenant_membership.tenant_id)
                tenant_name = tenant_membership.tenant.name if tenant_membership.tenant else None

            user_profile = {
                "user": {
                    "email": user.email,
                    "full_name": user.fullName,
                    "role": effective_role,
                    "tenant_id": tenant_id,
                    "tenant_name": tenant_name
                }
            }

            return mtns_session, user_profile

    async def get_current_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch current user profile by ID."""
        async with self.uow:
            session = self.uow.session
            stmt = select(UserModel).options(
                selectinload(UserModel.tenantMemberships).selectinload(UserTenantModel.tenant)
            ).where(UserModel.id == user_id)
            
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise UnauthorizedError("User not found.")

            tenant_membership = None
            if user.role != "super-admin" and user.tenantMemberships:
                for membership in user.tenantMemberships:
                    if membership.isActive:
                        tenant_membership = membership
                        break

            effective_role = user.role
            tenant_id = None
            tenant_name = None

            if effective_role != "super-admin" and tenant_membership:
                effective_role = tenant_membership.role
                tenant_id = str(tenant_membership.tenant_id)
                tenant_name = tenant_membership.tenant.name if tenant_membership.tenant else None

            return {
                "user": {
                    "email": user.email,
                    "full_name": user.fullName,
                    "role": effective_role,
                    "tenant_id": tenant_id,
                    "tenant_name": tenant_name
                }
            }
