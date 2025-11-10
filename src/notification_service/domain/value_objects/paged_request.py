from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SortDirection(str, Enum):
    """Sort direction enum."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class PagedRequest:
    """Request model for pagination."""
    page: int = 1
    page_size: int = 10
    sort_by: Optional[str] = None
    sort_direction: SortDirection = SortDirection.ASC

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")
        if isinstance(self.sort_direction, str):
            self.sort_direction = SortDirection(self.sort_direction.lower())
