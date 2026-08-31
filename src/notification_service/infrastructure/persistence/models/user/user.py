from datetime import datetime

from sqlalchemy import (CheckConstraint, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index)
from sqlalchemy.orm import relationship
from ..base import BaseModel

class UserModel(BaseModel):
    """SQLAlchemy model for users.

    Stores local user identity, linked to Keycloak via keycloak_id.
    
    """
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN ('super-admin', 'user')",
            name="chk_user_role_valid",
        ),
    )

    keycloakId = Column(String, name="keycloakId", unique=True, nullable=False, index=True)
    email = Column(String, name="email", unique=True, nullable=False, index=True)
    fullName = Column(String, name="fullName", nullable=False)
    role = Column(String(50), name="role", nullable=False, default="user", index=True)
    isActive = Column(Boolean, name="isActive", nullable=False, default=True)
    
    createdAt = Column(DateTime, name="createdAt", nullable=False, default=datetime.now())
    updatedAt = Column(DateTime, name="updatedAt", nullable=False, default=datetime.now(), onupdate=datetime.now())
    
    # Relationships to user_tenants
    tenantMemberships = relationship(
        "UserTenantModel", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    