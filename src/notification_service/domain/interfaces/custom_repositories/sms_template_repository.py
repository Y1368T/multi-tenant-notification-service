from typing import Optional
from notification_service.domain.interfaces.igeneric_repository import IGenericRepository
from typing import TypeVar, Generic
T = TypeVar('T')



class ISMSTemplateRepository(IGenericRepository[T],Generic[T]):
    """Interface for SMS Template Repository."""

    def __init__(self):
        super().__init__()