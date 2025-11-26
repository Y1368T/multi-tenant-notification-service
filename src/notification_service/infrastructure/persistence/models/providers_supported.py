from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from notification_service.infrastructure.persistence.models.base import Base
import uuid
from datetime import datetime
from .base import BaseModel


class ProviderModel(BaseModel):
    __tablename__ = "providers"

    providerName = Column(String, name="providerName", unique=True, nullable=False, index=True)
    displayName = Column(String, name="displayName", nullable=False)
    channel = Column(String, nullable=False, index=True)
    description = Column(String)
    docsUrl = Column(String, name="docsUrl")
    testEndpoint = Column(String, name="testEndpoint")
    configSchema = Column(JSON, name="configSchema", nullable=False)
    uiSchema = Column(JSON, name="uiSchema")
    isActive = Column(Boolean, name="isActive", default=True, nullable=False)