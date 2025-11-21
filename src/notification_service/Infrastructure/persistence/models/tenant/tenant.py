from sqlalchemy import Column, String, Boolean,Integer
from sqlalchemy.orm import relationship
from ..base import BaseModel
from sqlalchemy.dialects.postgresql import ARRAY

class TenantModel(BaseModel):
    __tablename__ = "tenants"

    name = Column(String, unique=True, index=True, nullable=False)
    isActive = Column(Boolean, name="isActive", default=True)
    prefix = Column(String(10), unique=True, index=True, nullable=False)
    apiKeys = Column(String, name="apiKeys", nullable=True)
    supportedChannels = Column(ARRAY(String), name="supportedChannels", nullable=True)
    preferedCommunicationMethod=Column(String, name="preferedCommunicationMethod", nullable=False,default="rest")  # Rest , Kafka , RabbitMq , gRPC
    rateLimitPerMinute = Column(Integer, name="rateLimitPerMinute", default=60)
    rateLimitPerHour = Column(Integer, name="rateLimitPerHour", default=1000)
    rateLimitPerDay = Column(Integer, name="rateLimitPerDay", default=10000)
    
    emailConfigurations = relationship("TenantEmailConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    smsConfigurations = relationship("TenantSMSConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    smsTemplates = relationship("SmsTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    emailTemplates = relationship("EmailTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    inAppTemplates = relationship("InAppTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    inAppConfigurations = relationship("TenantInAppConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")