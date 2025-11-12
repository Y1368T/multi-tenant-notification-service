from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime,UUID
from datetime import datetime
Base = declarative_base()
class BaseModel(Base):
    __abstract__ = True

    id = Column(UUID, primary_key=True, index=True)
    createdAt = Column(DateTime, name="created_at", default=datetime.utcnow)
    updatedAt = Column(DateTime, name="updated_at", default=datetime.utcnow, onupdate=datetime.utcnow)