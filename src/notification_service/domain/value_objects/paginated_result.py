from dataclasses import dataclass
from typing import List, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
TEntity = TypeVar('TEntity')

@dataclass
class PaginatedResult(Generic[TEntity]):
    """Container for paginated results."""
    items: List[TEntity]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
class PaginatedResponseDTO(Generic[TEntity], BaseModel):
    """Generic paginated response DTO."""
    
    model_config = ConfigDict(from_attributes=True)
    
    items: list[TEntity]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool