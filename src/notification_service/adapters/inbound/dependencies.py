from typing import List, Optional, Callable, Dict, Any, Union
from fastapi import Request, HTTPException, status


def require_role(allowed_roles: Union[str, List[str]]) -> Callable[[Request], Dict[str, Any]]:
    """
    FastAPI dependency factory that returns a dependency function
    to enforce role-based access control.
    
    Args:
        allowed_roles: A string or list of roles (e.g., ['super-admin', 'tenant-manager'])
                       that are permitted to access the endpoint.
                       
    Returns:
        A callable dependency that checks the user role.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def role_checker(request: Request) -> Dict[str, Any]:
        if not hasattr(request.state, "user"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session not found in request state."
            )
        
        user_data = request.state.user
        if not user_data or not isinstance(user_data, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user session data."
            )

        role = user_data.get("role")
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No role assigned to this user."
            )

        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized. Allowed roles: {', '.join(allowed_roles)}"
            )
        
        return user_data

    return role_checker


def get_tenant_scope(request: Request) -> Optional[str]:
    """
    FastAPI dependency to retrieve the tenant scope for the current request.
    
    If the user is a 'tenant-manager', it returns their tenant_id to force 
    data isolation/filtering on subsequent database queries.
    
    If the user is a 'super-admin', it returns None, signifying unrestricted access.
    
    Returns:
        The tenant_id as a string, or None for super-admins.
        
    Raises:
        HTTPException: If the session is invalid, the role is unknown, 
                       or a tenant-manager lacks a tenant_id.
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session not found in request state."
        )
    
    user_data = request.state.user
    if not user_data or not isinstance(user_data, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user session data."
        )

    role = user_data.get("role")
    
    if role == "super-admin":
        return None
    
    if role == "tenant-manager":
        tenant_id = user_data.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant manager has no associated tenant_id."
            )
        return tenant_id
        
    # Default fallback for unknown roles: deny access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Role '{role}' is not authorized for tenant-scoped operations."
    )

def verify_tenant_access(tenant_id: str, request: Request) -> bool:
    """
    FastAPI dependency to verify that the user has access to the specified tenant_id.
    Super-admins can access any tenant. Tenant-managers can only access their own.
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session not found in request state."
        )
    
    user_data = request.state.user
    role = user_data.get("role")
    
    if role == "super-admin":
        return True
        
    if role == "tenant-manager":
        user_tenant_id = user_data.get("tenant_id")
        if not user_tenant_id or str(user_tenant_id) != str(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot access resources belonging to other tenants."
            )
        return True
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Role '{role}' is not authorized."
    )
