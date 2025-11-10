from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from notification_service.infrastructure.persisitence.models.base import Base
import uuid
from datetime import datetime
from .base import BaseModel


class ProviderModel(BaseModel):
    __tablename__ = "providers"

    provider_name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    channel = Column(String, nullable=False, index=True)
    description = Column(String)
    docs_url = Column(String)
    test_endpoint = Column(String)
    config_schema = Column(JSON, nullable=False)
    ui_schema = Column(JSON)
    is_active = Column(Boolean, default=True, nullable=False)