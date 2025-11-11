from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from notification_service.infrastructure.persisitence.models.base import Base
import uuid
from datetime import datetime
from .base import BaseModel


class ProviderModel(BaseModel):
    __tablename__ = "providers"

    providerName = Column(String, name="provider_name", unique=True, nullable=False, index=True)
    displayName = Column(String, name="display_name", nullable=False)
    channel = Column(String, nullable=False, index=True)
    description = Column(String)
    docsUrl = Column(String, name="docs_url")
    testEndpoint = Column(String, name="test_endpoint")
    configSchema = Column(JSON, name="config_schema", nullable=False)
    uiSchema = Column(JSON, name="ui_schema")
    isActive = Column(Boolean, name="is_active", default=True, nullable=False)