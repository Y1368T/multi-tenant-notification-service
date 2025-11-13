from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Dict, Any, Optional


@dataclass
class Provider:
    """Domain entity for notification providers."""
    id: UUID = field(default_factory=uuid4)
    providerName: str = ""
    displayName: str = ""
    channel: str = ""  # sms, email, push, whatsapp
    description: Optional[str] = None
    docsUrl: Optional[str] = None
    testEndpoint: Optional[str] = None
    configSchema: Dict[str, Any] = field(default_factory=dict)
    uiSchema: Optional[Dict[str, Any]] = None
    isActive: bool = True
    createdAt: datetime = field(default_factory=datetime.utcnow)
    updatedAt: datetime = field(default_factory=datetime.utcnow)