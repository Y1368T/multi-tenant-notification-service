from sqlalchemy import Column, String, Boolean,Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from ..base import BaseModel

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
    # Callback configuration for fire-and-forget mode
    callbackUrl = Column(String, name="callbackUrl", nullable=True)  # Webhook URL for notification status
    callbackHeaders = Column(JSON, name="callbackHeaders", nullable=True)  # Optional auth headers
    
    sentCount = Column(Integer, name="sentCount", default=0)
    sentCount30d = Column(Integer, name="sentCount30d", default=0)
    
    emailConfigurations = relationship("TenantEmailConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    smsConfigurations = relationship("TenantSMSConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    smsTemplates = relationship("SmsTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    emailTemplates = relationship("EmailTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    inAppTemplates = relationship("InAppTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    inAppConfigurations = relationship("TenantInAppConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    # telegramConfigurations = relationship("TenantTelegramConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    # telegramTemplates = relationship("TelegramTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    userMemberships = relationship("UserTenantModel", back_populates="tenant", cascade="all, delete-orphan")
    #new
    whatsAppConfigurations = relationship("TenantWhatsAppConfigurationModel", back_populates="tenant", cascade="all, delete-orphan")
    whatsAppTemplates = relationship("WhatsAppTemplateModel", back_populates="tenant", cascade="all, delete-orphan")
    #new