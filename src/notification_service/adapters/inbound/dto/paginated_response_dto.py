"""Generic paginated response DTO."""
from pydantic import BaseModel, ConfigDict, Field
from typing import TypeVar, Generic, List

T = TypeVar('T')


class PaginatedResponseDTO(BaseModel, Generic[T]):
    """Generic paginated response DTO that can be used with any entity type."""
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    items: List[T]
    totalCount: int = Field(alias="totalCount")
    page: int
    pageSize: int = Field(alias="pageSize")
    totalPages: int = Field(alias="totalPages")
    hasNext: bool = Field(alias="hasNext")
    hasPrevious: bool = Field(alias="hasPrevious")
