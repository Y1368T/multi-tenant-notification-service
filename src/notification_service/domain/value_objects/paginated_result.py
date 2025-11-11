from dataclasses import dataclass
from typing import List, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
TEntity = TypeVar('TEntity')

@dataclass
class PaginatedResult(Generic[TEntity]):
    """Container for paginated results."""
    items: List[TEntity]
    totalCount: int
    page: int
    pageSize: int
    totalPages: int
    hasNext: bool
    hasPrevious: bool
    
class PaginatedResponseDTO(Generic[TEntity], BaseModel):
    """Generic paginated response DTO."""
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=False)
    
    items: list[TEntity]
    totalCount: int = Field(alias="total_count")
    page: int
    pageSize: int = Field(alias="page_size")
    totalPages: int = Field(alias="total_pages")
    hasNext: bool = Field(alias="has_next")
    hasPrevious: bool = Field(alias="has_previous")