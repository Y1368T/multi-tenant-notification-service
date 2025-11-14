from sqlalchemy import Column, String, Boolean,Integer
from sqlalchemy.orm import relationship
from ..base import BaseModel
from sqlalchemy.dialects.postgresql import ARRAY

class TenantModel(BaseModel):
    __tablename__ = "tenants"

    name = Column(String, unique=True, index=True, nullable=False)
    isActive = Column(Boolean, name="is_active", default=True)
    prefix = Column(String(10), unique=True, index=True, nullable=False)
    apiKeys = Column(String, name="api_keys", nullable=True)
    supportedChannels = Column(ARRAY(String), name="supported_channels", nullable=True)
    preferedCommunicationMethod=Column(String, name="prefered_communication_method", nullable=False,default="rest")  # Rest , Kafka , RabbitMq , gRPC
    rateLimitPerMinute = Column(Integer, name="rate_limit_per_minute", default=60)
    rateLimitPerHour = Column(Integer, name="rate_limit_per_hour", default=1000)
    rateLimitPerDay = Column(Integer, name="rate_limit_per_day", default=10000)
    
    emailConfigurations = relationship("TenantEmailConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    smsConfigurations = relationship("TenantSMSConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    smsTemplates = relationship("SmsTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    emailTemplates = relationship("EmailTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    inAppTemplates = relationship("InAppTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    inAppConfigurations = relationship("TenantInAppConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")