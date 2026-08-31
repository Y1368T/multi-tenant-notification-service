"""Request and response DTOs for authentication endpoints."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


#REQUEST DTOs

class RegisterRequestDTO(BaseModel):
    """Body for POST /auth/register"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    fullName: str = Field(..., min_length=1, description="Full name of the user")
    tenantId: Optional[UUID] = Field(None, description="Tenant to join on register")
    role: str = Field("tenant-manager", description="Role: 'super-admin' or 'tenant-manager'")

    @field_validator("role")
    @classmethod
    def validateRole(cls, v: str) -> str:
        if v not in ("super-admin", "tenant-manager", "admin", "member"):
            raise ValueError("role must be 'super-admin', 'tenant-manager', 'admin', or 'member'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123",
                "fullName": "John Doe",
                "tenantId": "uuid-of-tenant",
                "role": "tenant-manager"
            }
        }
    }


class LoginRequestDTO(BaseModel):
    """Body for POST /auth/login"""
    email: str
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {"email": "john@example.com", "password": "SecurePass123"}
        }
    }


class LogoutRequestDTO(BaseModel):
    """Body for POST /auth/logout"""
    refreshToken: str = Field(..., description="The refresh token to revoke")


class RefreshRequestDTO(BaseModel):
    """Body for POST /auth/refresh"""
    refreshToken: str = Field(..., description="The current refresh token")


#RESPONSE DTOs

class TenantMembershipDTO(BaseModel):
    """Tenant membership info embedded in user responses."""
    tenantId: UUID
    tenantName: str
    tenantPrefix: str
    role: str
    isActive: bool


class UserProfileDTO(BaseModel):
    """Full user profile (used in /me and register response)."""
    userId: UUID
    email: str
    fullName: str
    isActive: bool
    tenants: List[TenantMembershipDTO] = []
    createdAt: datetime


class AuthResponseDTO(BaseModel):
    """Returned after login and register (tokens + user profile)."""
    accessToken: str
    refreshToken: str
    sessionToken: Optional[str] = None
    tokenType: str = "Bearer"
    expiresIn: int
    user: UserProfileDTO


class TokenResponseDTO(BaseModel):
    """Returned after a refresh (tokens only)."""
    accessToken: str
    refreshToken: str
    sessionToken: Optional[str] = None
    tokenType: str = "Bearer"
    expiresIn: int


class MessageResponseDTO(BaseModel):
    """Generic message response (used for logout)."""
    message: str
