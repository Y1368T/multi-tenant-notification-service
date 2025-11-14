from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from enum import Enum
from typing import Any, Dict, List
import re
from notification_service.shared.validators.input_validators import validate_string_input, validate_uuid_string

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
    id: Optional[str] = Field(None, description="Filter by entity ID (for single entity retrieval)")
    
    model_config = ConfigDict(populate_by_name=True)
    
    @field_validator('sortBy')
    @classmethod
    def validate_sort_by(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort by field name."""
        if v is None:
            return v
        
        # Sanitize and validate field name
        sanitized = validate_string_input(
            v,
            field_name='sortBy',
            max_length=100,
            min_length=1
        )
        
        # Field name should be alphanumeric with underscores (SQL-safe)
        if not re.match(r'^[a-zA-Z0-9_]+$', sanitized):
            raise ValueError("Sort field name must contain only letters, numbers, and underscores")
        
        return sanitized
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, v: Optional[str]) -> Optional[str]:
        """Validate search text."""
        if v is None or v == "":
            return None
        
        # Sanitize search text
        sanitized = validate_string_input(
            v,
            field_name='search',
            max_length=256,
            min_length=1,
            allow_html=False
        )
        
        return sanitized
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate entity ID (UUID format)."""
        if v is None or v == "":
            return None
        
        # Validate UUID format
        try:
            validated = validate_uuid_string(v)
            return validated
        except ValueError as e:
            raise ValueError(f"Invalid ID format: {str(e)}")


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
    
    @field_validator('relationshipPath')
    @classmethod
    def validate_relationship_path(cls, v: str) -> str:
        """Validate relationship path (e.g., 'template.tenant')."""
        if not v or not isinstance(v, str):
            raise ValueError("Relationship path must be a non-empty string")
        
        # Sanitize relationship path
        sanitized = validate_string_input(
            v,
            field_name='relationshipPath',
            max_length=200,
            min_length=1
        )
        
        # Relationship path should be dot-separated alphanumeric with underscores
        # e.g., "template.tenant", "user.profile"
        if not re.match(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$', sanitized):
            raise ValueError("Relationship path must be dot-separated field names (e.g., 'template.tenant')")
        
        return sanitized
    
    @field_validator('field')
    @classmethod
    def validate_field(cls, v: str) -> str:
        """Validate field name."""
        if not v or not isinstance(v, str):
            raise ValueError("Field name must be a non-empty string")
        
        # Sanitize field name
        sanitized = validate_string_input(
            v,
            field_name='field',
            max_length=100,
            min_length=1
        )
        
        # Field name should be alphanumeric with underscores (SQL-safe)
        if not re.match(r'^[a-zA-Z0-9_]+$', sanitized):
            raise ValueError("Field name must contain only letters, numbers, and underscores")
        
        return sanitized
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        """Validate filter value."""
        # If value is a string, sanitize it
        if isinstance(v, str):
            sanitized = validate_string_input(
                v,
                field_name='value',
                max_length=500,
                allow_html=False
            )
            return sanitized
        
        # For other types (int, bool, list, etc.), return as-is
        # Additional validation can be added based on specific needs
        return v


class PaginatedRequest(BaseModel):
    page: int = Field(1, ge=1)
    pageSize: int = Field(10, ge=1, le=100)
    sortBy: Optional[str] = None
    sortDirection: SortDirection = SortDirection.DESC
    searchText: Optional[str] = None
    searchFields: Optional[List[str]] = None
    filters: Dict[str, Any] = {}
    relatedFilters: List[RelatedFilter] = []