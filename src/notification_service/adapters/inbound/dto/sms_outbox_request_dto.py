from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class SMSOutboxRequestDTO(BaseModel):
    recipient_number: str
    message_content: str
    idempotency_key: str
    template_id: UUID
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    provider_attempted: Optional[str] = None
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    status: str = "pending"
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)


class SMSOutbocFilterDTO(BaseModel):
    page: int = 1
    page_size: int = 10
    sort_by: str = "created_at"
    sort_order: str = "desc"
    filters: Optional[Dict[str, Any]] = None
    includes: Optional[List[str]] = None
    search: Optional[str] = None
    search_fields: Optional[List[str]] = None
    search_op: Optional[str] = None
    search_value: Optional[str] = None