from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class AdminUserResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: str
    fullName: str
    role: str
    isActive: bool
    createdAt: datetime
    updatedAt: datetime
    
    # We can include tenant associations
    tenants: List[str] = []

class AdminCreateUserRequestDTO(BaseModel):
    email: str
    full_name: str
    role: str
    tenant_id: UUID

class AdminUpdateUserRequestDTO(BaseModel):
    full_name: Optional[str] = None
    tenant_id: Optional[UUID] = None
    is_active: Optional[bool] = None
