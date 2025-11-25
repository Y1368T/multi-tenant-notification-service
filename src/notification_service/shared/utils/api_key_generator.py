"""Utility functions for generating secure API keys."""
import secrets
import string


def generate_api_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure API key.
    
    Args:
        length: Length of the API key (default: 32 characters)
        
    Returns:
        A secure random API key string
    """
    # Use URL-safe base64 characters for API keys
    # This includes: A-Z, a-z, 0-9, -, _
    alphabet = string.ascii_letters + string.digits + "-_"
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key


def generate_api_key_with_prefix(prefix: str, length: int = 32) -> str:
    """
    Generate an API key with a tenant prefix for easier identification.
    
    Args:
        prefix: Tenant prefix to include in the API key
        length: Total length of the API key (default: 32)
        
    Returns:
        A secure random API key with prefix (format: prefix_xxxxxxxx)
    """
    # Reserve space for prefix and separator
    key_length = max(16, length - len(prefix) - 1)  # At least 16 chars for the key part
    alphabet = string.ascii_letters + string.digits + "-_"
    random_part = ''.join(secrets.choice(alphabet) for _ in range(key_length))
    return f"{prefix}_{random_part}"

