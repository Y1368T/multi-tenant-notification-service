from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class User:
    """Domain entity for users.

    Stores local user identity. Keycloak is the source of truth
    for credentials. keycloakId links this record to the Keycloak user.

    role is platform-level: 'super-admin' or 'user'.
    Tenant-level roles live in UserTenant.
    """
    id: UUID
    keycloakId: str          # The 'sub' claim from Keycloak JWT
    email: str
    fullName: str
    role: str = "user"       # 'super-admin' or 'user'
    isActive: bool = True
    createdAt: datetime = field(default_factory=datetime.now)
    updatedAt: datetime = field(default_factory=datetime.now)
