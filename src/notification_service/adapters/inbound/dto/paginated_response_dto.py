"""Generic paginated response DTO."""
from pydantic import BaseModel, ConfigDict
from typing import TypeVar, Generic, List

T = TypeVar('T')


class PaginatedResponseDTO(BaseModel, Generic[T]):
    """Generic paginated response DTO that can be used with any entity type."""
    
    model_config = ConfigDict(from_attributes=True)
    
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
