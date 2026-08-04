from fastapi import Depends, Response
from qena_shared_lib.http import ControllerBase, api_controller, post

from notification_service.adapters.inbound.dto.auth_dto import LoginRequestDTO, LoginResponseDTO, UserResponseDTO
from uuid import uuid4
import jwt
from datetime import datetime, timedelta, timezone

@api_controller(prefix="/auth", tags=["Authentication"])
class AuthController(ControllerBase):
    def __init__(self):
        # In a real implementation, a service would be injected here to handle
        # the Keycloak validation and DB session management.
        pass

    @post("/login", response_model=LoginResponseDTO)
    async def login(self, response: Response, request: LoginRequestDTO) -> LoginResponseDTO:
        """
        Authenticate user credentials, return session data and set HTTP-only cookie.
        NOTE: This is currently stubbed as per requirements.
        """
        # Stub logic: generate a fake token and user data
        expires_in = 28800  # 8 hours
        exp_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        # Example user payload
        user_id = str(uuid4())
        tenant_id = str(uuid4()) if "tenant" in request.email else None
        role = "tenant-manager" if tenant_id else "super-admin"
        
        payload = {
            "session_id": str(uuid4()),
            "user_id": user_id,
            "email": request.email,
            "full_name": "Stub User",
            "role": role,
            "tenant_id": tenant_id,
            "issued_at": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(exp_time.timestamp())
        }
        
        # We don't have SESSION_SIGNING_KEY in environment for this stub, so we use a dummy key
        token = jwt.encode(payload, "dummy_secret_key", algorithm="HS256")
        
        # Set the HTTP-only cookie
        response.set_cookie(
            key="mtns_session",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=expires_in,
            path="/"
        )
        
        user_response = UserResponseDTO(
            email=request.email,
            full_name="Stub User",
            role=role,
            tenant_id=tenant_id
        )
        
        return LoginResponseDTO(
            session_token=token,
            expires_in=expires_in,
            user=user_response
        )

    @post("/logout", status_code=204)
    async def logout(self, response: Response):
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
        # In real implementation, also tell backend session storage / Keycloak to logout
        return None
