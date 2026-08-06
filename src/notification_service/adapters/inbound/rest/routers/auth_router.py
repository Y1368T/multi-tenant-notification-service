"""Authentication router — handles register, login, logout, refresh, /me."""
from fastapi import Depends
from notification_service.application.services.auth_service import AuthService
from notification_service.adapters.inbound.rest.dependencies.auth_dependency import get_current_user
from notification_service.domain.entities.user.user import User
from notification_service.adapters.inbound.dto.auth_dto import (
    RegisterRequestDTO,
    LoginRequestDTO,
    LogoutRequestDTO,
    RefreshRequestDTO,
    AuthResponseDTO,
    TokenResponseDTO,
    UserProfileDTO,
    MessageResponseDTO,
)
from qena_shared_lib.http import ControllerBase, api_controller, get, post


@api_controller(prefix="/auth", tags=["Authentication"])
class AuthController(ControllerBase):
    """Controller for all authentication endpoints."""

    def __init__(self, authService: AuthService = Depends()):
        self.authService = authService

    @post("/register", response_model=AuthResponseDTO, status_code=201)
    async def register(self, body: RegisterRequestDTO) -> AuthResponseDTO:
        """Register a new user and return tokens.
        
        - Creates user in Keycloak
        - Creates local user record
        - Links user to tenant (if tenantId provided)
        - Returns access + refresh tokens and user profile
        """
        return await self.authService.register(
            email=body.email,
            password=body.password,
            fullName=body.fullName,
            tenantId=body.tenantId,
            role=body.role,
        )

    @post("/login", response_model=AuthResponseDTO)
    async def login(self, body: LoginRequestDTO) -> AuthResponseDTO:
        """Authenticate and return tokens.
        
        Keycloak validates the credentials. Returns access + refresh tokens
        and the user profile with tenant memberships.
        """
        return await self.authService.login(
            email=body.email,
            password=body.password,
        )

    @post("/logout", response_model=MessageResponseDTO)
    async def logout(self, body: LogoutRequestDTO) -> MessageResponseDTO:
        """Revoke the refresh token in Keycloak.
        
        After this, the client must discard both tokens.
        """
        await self.authService.logout(refreshToken=body.refreshToken)
        return MessageResponseDTO(message="Logged out successfully")

    @post("/refresh", response_model=TokenResponseDTO)
    async def refresh(self, body: RefreshRequestDTO) -> TokenResponseDTO:
        """Exchange a refresh token for a new token pair."""
        return await self.authService.refresh(refreshToken=body.refreshToken)

    @get("/me", response_model=UserProfileDTO)
    async def me(
        self,
        currentUser: User = Depends(get_current_user),
    ) -> UserProfileDTO:
        """Return the currently authenticated user's profile.
        
        Requires: Authorization: Bearer <access_token>
        """
        return await self.authService.getCurrentUser(
            keycloakId=currentUser.keycloakId
        )
