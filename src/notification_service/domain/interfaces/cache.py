
from abc import ABC, abstractmethod
from typing import  TypeVar,Optional,Any
class ICachedRepository(ABC):
    """Interface for cached repository operations."""
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from the cache by key.
        
        Args:
            key (str): The cache key.
        Returns:
            Cached value (desrialized from JSON), or None if not found.
        
        
        """
        
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set an item in the cache.
        
        Args:
            key (str): The cache key.
            value (Any): The value to cache (will be serialized to JSON).
            expire (Optional[int]): Expiration time in seconds.
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete an item from the cache by key.
        
        Args:
            key (str): The cache key.
        """
        pass   
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.
        
        Args:
            key (str): The cache key.
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key (str): The cache key.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        pass
    @abstractmethod
    async def getExpiryTime(self, key: str) -> Optional[int]:
        """Get the expiration time for a cache key.

        Args:
            key (str): The cache key.

        Returns:
            Optional[int]: Expiration time in seconds, or None if not set.
            return should be in seconds 
        """
        pass