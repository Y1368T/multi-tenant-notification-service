from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Tenant:
    """Domain entity for tenants"""
    
    id: UUID
    name: str
    prefix: str
    isActive: bool = True
    supportedChannels: list[str] = field(default_factory=list)
    apiKeys: str = ""
    preferedCommunicationMethod:str = "rest"  # Rest , Kafka , RabbitMq , gRPC
    rateLimitPerMinute: int = 60
    rateLimitPerHour: int = 1000
    rateLimitPerDay: int = 10000
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)