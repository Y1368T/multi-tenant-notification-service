from fastapi import Response, Request, HTTPException, status
from qena_shared_lib.http import ControllerBase, api_controller, post
from qena_shared_lib.dependencies.http import get_service

from notification_service.adapters.inbound.dto.auth_dto import LoginRequestDTO, LoginResponseDTO, UserResponseDTO
from notification_service.config.settings import Settings
from notification_service.infrastructure.services.redis_session_manager import RedisSessionManager
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.persistence.models.user.user import UserModel
from notification_service.infrastructure.persistence.models.user.user_tenant import UserTenantModel
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from uuid import uuid4
import jwt
import httpx
from datetime import datetime, timezone

@api_controller(prefix="/auth", tags=["Authentication"])
class AuthController(ControllerBase):
    def __init__(self):
        pass

    @post("/login", response_model=LoginResponseDTO)
    async def login(self, request: Request, response: Response, login_req: LoginRequestDTO) -> LoginResponseDTO:
        """
        Authenticate user credentials against Keycloak, create a backend session in Redis,
        and set an HTTP-only secure cookie for the portal.
        """
        settings = get_service(request.app, Settings)
        redis_session_manager = get_service(request.app, RedisSessionManager)
        db = get_service(request.app, Database)

        # 1. Authenticate against Keycloak via ROPC
        keycloak_token_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": settings.keycloak_client_id,
            "username": login_req.email,
            "password": login_req.password,
        }
        
        if settings.keycloak_client_secret:
            data["client_secret"] = settings.keycloak_client_secret

        try:
            async with httpx.AsyncClient() as client:
                kc_response = await client.post(keycloak_token_url, data=data, timeout=5.0)
                
            if kc_response.status_code == 401:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
            
            kc_response.raise_for_status()
            token_data = kc_response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Keycloak error: {e}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to connect to Keycloak: {e}")

        # 2. Extract Keycloak 'sub' claim
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        try:
            # We trust the Keycloak response directly over HTTPS, no need to verify signature here
            payload = jwt.decode(access_token, options={"verify_signature": False})
            sub = payload.get("sub")
            if not sub:
                raise ValueError("Missing 'sub' claim in Keycloak token.")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Invalid Keycloak token format: {e}")

        # 3. Query our database
        async with db.session_factory() as db_session:
            stmt = select(UserModel).options(
                joinedload(UserModel.tenantMemberships).joinedload(UserTenantModel.tenant)
            ).where(UserModel.keycloakId == sub)
            
            result = await db_session.execute(stmt)
            user = result.unique().scalar_one_or_none()

            # 4. Validate user
            if not user:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not provisioned in MTNS.")
            
            if not user.isActive:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated.")

            # Resolve tenant info
            tenant_id = None
            tenant_name = None
            
            if user.role == "tenant-manager":
                # Find the first active tenant manager membership
                for membership in user.tenantMemberships:
                    if membership.role == "tenant-manager" and membership.isActive:
                        if membership.tenant and membership.tenant.isActive:
                            tenant_id = membership.tenant_id
                            tenant_name = membership.tenant.name
                            break
                
                if not tenant_id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no active tenant memberships.")

            # 5. Create Redis session
            user_session_data = {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.fullName,
                "role": user.role,
                "tenant_id": str(tenant_id) if tenant_id else None
            }
            
            session_id = await redis_session_manager.create_session(
                user_data=user_session_data,
                refresh_token=refresh_token,
                ttl_seconds=28800
            )

        # 6. Set signed mtns_session cookie
        session_token_payload = {
            "session_id": session_id,
            "role": user.role,
            "issued_at": int(datetime.now(timezone.utc).timestamp())
        }
        
        signed_token = jwt.encode(
            session_token_payload, 
            settings.session_signing_key, 
            algorithm="HS256"
        )

        response.set_cookie(
            key="mtns_session",
            value=signed_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=28800,
            path="/"
        )

        # 7. Return HTTP 200 JSON
        user_response = UserResponseDTO(
            email=user.email,
            full_name=user.fullName,
            role=user.role,
            tenant_id=tenant_id,
            tenant_name=tenant_name
        )
        
        return LoginResponseDTO(user=user_response)

    @post("/logout", status_code=204)
    async def logout(self, request: Request, response: Response):
        """
        Invalidate session and clear the HTTP-only cookie.
        """
        response.delete_cookie(
            key="mtns_session",
            path="/",
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        # Optionally invalidate from Redis
        try:
            token = request.cookies.get("mtns_session")
            if token:
                settings = get_service(request.app, Settings)
                redis_session_manager = get_service(request.app, RedisSessionManager)
                payload = jwt.decode(token, settings.session_signing_key, algorithms=["HS256"])
                session_id = payload.get("session_id")
                if session_id:
                    await redis_session_manager.delete_session(session_id)
        except Exception:
            pass # Ignore errors on logout
            
        return None
