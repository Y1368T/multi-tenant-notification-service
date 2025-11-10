from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from typing import Any, Dict, List
class SortDirection(str, Enum):
    """Sort direction enum."""
    ASC = "asc"
    DESC = "desc"

class PaginatedRequestDTO(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")
    sort_by: Optional[str] = Field(None, description="Sort by field")
    sort_direction: SortDirection = SortDirection.DESC
    search: Optional[str] = Field(None, max_length=256, description="Search text")
    tenant_id: Optional[str] = Field(None, description="Filter by tenant ID")


class FilterOp(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    ILIKE = "ilike"
    IN = "in"


class RelatedFilter(BaseModel):
    relationship_path: str
    field: str
    op: FilterOp = FilterOp.EQ
    value: Any


class PaginatedRequest(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_direction: SortDirection = SortDirection.DESC
    search_text: Optional[str] = None
    search_fields: Optional[List[str]] = None
    filters: Dict[str, Any] = {}
    related_filters: List[RelatedFilter] = []