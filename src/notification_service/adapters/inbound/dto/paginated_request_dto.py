from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from enum import Enum
from typing import Any, Dict, List
class SortDirection(str, Enum):
    """Sort direction enum."""
    ASC = "asc"
    DESC = "desc"

class PaginatedRequestDTO(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    pageSize: int = Field(10, ge=1, le=100, alias="page_size", description="Number of items per page")
    sortBy: Optional[str] = Field(None, alias="sort_by", description="Sort by field")
    sortDirection: SortDirection = Field(SortDirection.DESC, alias="sort_direction")
    search: Optional[str] = Field(None, max_length=256, description="Search text")
    tenantId: Optional[str] = Field(None, alias="tenant_id", description="Filter by tenant ID")
    
    model_config = ConfigDict(populate_by_name=True)


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
    relationshipPath: str = Field(alias="relationship_path")
    field: str
    op: FilterOp = FilterOp.EQ
    value: Any
    
    model_config = ConfigDict(populate_by_name=True)


class PaginatedRequest(BaseModel):
    page: int = Field(1, ge=1)
    pageSize: int = Field(10, ge=1, le=100)
    sortBy: Optional[str] = None
    sortDirection: SortDirection = SortDirection.DESC
    searchText: Optional[str] = None
    searchFields: Optional[List[str]] = None
    filters: Dict[str, Any] = {}
    relatedFilters: List[RelatedFilter] = []