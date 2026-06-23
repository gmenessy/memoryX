"""
Authentication Dependencies for FastAPI.

Provides reusable dependencies for protecting routes with JWT authentication
and role-based authorization.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.exceptions import AuthenticationError, AuthorizationError
from app.models.auth import Permission, TokenPayload, TokenType, UserRole
from app.services.auth_service import AuthService

# HTTP Bearer scheme for token authentication
security = HTTPBearer()


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session)
) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPayload:
    """
    Dependency to get current authenticated user from JWT token.

    Raises HTTP 401 if token is invalid.

    Usage:
        ```python
        @router.get("/protected")
        async def protected_route(current_user: TokenPayload = Depends(get_current_user)):
            return {"user_id": current_user.sub, "email": current_user.email}
        ```
    """
    try:
        return auth_service.verify_token(credentials.credentials, TokenType.ACCESS)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    current_user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Dependency to require admin role.

    Raises HTTP 403 if user is not admin.

    Usage:
        ```python
        @router.delete("/users/{user_id}")
        async def delete_user(current_admin: TokenPayload = Depends(require_admin)):
            # Only admins can delete users
            pass
        ```
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory to require specific roles.

    Args:
        *allowed_roles: List of allowed roles

    Usage:
        ```python
        @router.post("/memory")
        async def create_memory(
            current_user: TokenPayload = Depends(require_role(UserRole.USER, UserRole.ADMIN))
        ):
            # Both USER and ADMIN can create memories
            pass
        ```
    """
    async def role_checker(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if current_user.role not in allowed_roles and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: one of {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


def require_permission(permission: Permission):
    """
    Dependency factory to require specific permission.

    Args:
        permission: Required permission

    Usage:
        ```python
        @router.delete("/memory/{memory_id}")
        async def delete_memory(
            current_user: TokenPayload = Depends(require_permission(Permission.MEMORY_DELETE))
        ):
            # Only users with MEMORY_DELETE permission can delete
            pass
        ```
    """
    async def permission_checker(
        current_user: TokenPayload = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> TokenPayload:
        try:
            auth_service.check_permission(current_user.role, permission.value)
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            )
        return current_user

    return permission_checker


# Commonly used permission dependencies
RequireMemoryCreate = require_permission(Permission.MEMORY_CREATE)
RequireMemoryRead = require_permission(Permission.MEMORY_READ)
RequireMemoryUpdate = require_permission(Permission.MEMORY_UPDATE)
RequireMemoryDelete = require_permission(Permission.MEMORY_DELETE)

RequireEventCreate = require_permission(Permission.EVENT_CREATE)
RequireEventRead = require_permission(Permission.EVENT_READ)

RequireGovernanceRead = require_permission(Permission.GOVERNANCE_READ)
RequireGovernanceWrite = require_permission(Permission.GOVERNANCE_WRITE)
RequireGovernanceAdmin = require_permission(Permission.GOVERNANCE_ADMIN)

RequireGraphRead = require_permission(Permission.GRAPH_READ)
RequireGraphWrite = require_permission(Permission.GRAPH_WRITE)
