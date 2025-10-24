from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime,UUID
from datetime import datetime
Base = declarative_base()
class BaseModel(Base):
    __abstract__ = True

    id = Column(UUID, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)