from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from notification_service.infrastructure.persistence.models.base import BaseModel

class MessageAggregateModel(BaseModel):
    __tablename__ = "message_aggregates_hourly"
    
    timeBucket = Column(DateTime(timezone=True), nullable=False, index=True)
    tenantId = Column(UUID(as_uuid=True), nullable=True, index=True)
    channel = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, index=True)
    messageCount = Column(Integer, nullable=False, default=0)
