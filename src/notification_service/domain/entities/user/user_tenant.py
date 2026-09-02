from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class UserTenant:
    """Domain entity for the user-tenant membership.
    
    Represents a user's membership within a specific tenant,
    including their role within that tenant.
    
    Composite key: (userId, tenantId)
    """
    userId: UUID
    tenantId: UUID
    role: str = "member"         
    isActive: bool = True
    joinedAt: datetime = field(default_factory=datetime.utcnow)

    tenantName: str = ""
    tenantPrefix: str = ""
    userEmail: str = ""
