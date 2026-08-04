from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

class LoginRequestDTO(BaseModel):
    email: EmailStr
    password: str

class UserResponseDTO(BaseModel):
    email: str
    full_name: str
    role: str
    tenant_id: Optional[UUID] = None

class LoginResponseDTO(BaseModel):
    session_token: str
    expires_in: int
    user: UserResponseDTO
