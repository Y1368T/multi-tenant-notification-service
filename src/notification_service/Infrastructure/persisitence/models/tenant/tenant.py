from sqlalchemy import Column, String, Boolean,Integer
from sqlalchemy.dialects.postgresql import relationship
from ..base import BaseModel

class TenantModel(BaseModel):
    __tablename__ = "tenants"

    name = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    prefix = Column(String, unique=True, index=True, nullable=False, length=10)
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)
    
    email_configurations = relationship("TenantEmailConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    sms_configurations = relationship("TenantSMSConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    sms_templates = relationship("SMSTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    email_templates = relationship("EmailTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    in_app_templates = relationship("InAppTemplateModel", back_populates="tenant", cascade="all, delete-orphan")