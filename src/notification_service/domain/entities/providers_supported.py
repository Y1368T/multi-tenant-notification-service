from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Dict, Any, Optional


@dataclass
class Provider:
    """Domain entity for notification providers."""
    id: UUID = field(default_factory=uuid4)
    provider_name: str = ""
    display_name: str = ""
    channel: str = ""  # sms, email, push, whatsapp
    description: Optional[str] = None
    docs_url: Optional[str] = None
    test_endpoint: Optional[str] = None
    config_schema: Dict[str, Any] = field(default_factory=dict)
    ui_schema: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)