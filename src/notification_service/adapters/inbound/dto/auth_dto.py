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
    tenant_name: Optional[str] = None

class LoginResponseDTO(BaseModel):
    user: UserResponseDTO

class AuthMeResponseDTO(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    tenant_id: Optional[UUID] = None
    tenant_name: Optional[str] = None
