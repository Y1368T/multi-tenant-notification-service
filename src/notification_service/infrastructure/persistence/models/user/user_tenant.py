from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from notification_service.infrastructure.persistence.models.base import Base

class UserTenantModel(Base):
    """SQLAlchemy model for user_tenants."""
    __tablename__ = "user_tenants"
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('tenant-manager', 'member')",
            name="chk_user_tenant_role_valid",
        ),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), name="userId", primary_key=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), name="tenantId", primary_key=True, nullable=False)
    role = Column(String(50), name="role", nullable=False, default="member", index=True)
    # status = Column(String, name="status", nullable=False)
    isActive = Column(Boolean, name="isActive", nullable=False, default=True)
    joinedAt = Column(DateTime, name="joinedAt", nullable=False, default=datetime.now())

    # Relationships
    user = relationship("UserModel", back_populates="tenantMemberships")
    tenant = relationship("TenantModel", back_populates="userMemberships")
