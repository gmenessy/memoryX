"""
Authentication and Authorization Models.

Defines schemas for user authentication, token management, and role-based access control.
"""
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    """User roles for Role-Based Access Control (RBAC)."""

    ADMIN = "admin"  # Full system access
    USER = "user"  # Standard user access
    READONLY = "readonly"  # Read-only access
    SYSTEM = "system"  # Internal system user


class TokenType(str, Enum):
    """Token types for JWT management."""

    ACCESS = "access"  # Short-lived access token (15 minutes)
    REFRESH = "refresh"  # Long-lived refresh token (7 days)


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.USER

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=50)
    role: UserRole | None = None
    disabled: bool | None = None


class UserResponse(BaseModel):
    """Schema for user response."""

    user_id: UUID
    email: EmailStr
    username: str
    role: UserRole
    disabled: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: TokenType
    expires_in: int  # Seconds until expiration


class TokenRefresh(BaseModel):
    """Schema for refreshing an access token."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # Subject (user_id)
    email: str
    role: UserRole
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    type: TokenType  # Token type


class Permission(str, Enum):
    """Specific permissions for granular access control."""

    # Memory permissions
    MEMORY_CREATE = "memory:create"
    MEMORY_READ = "memory:read"
    MEMORY_UPDATE = "memory:update"
    MEMORY_DELETE = "memory:delete"

    # Event permissions
    EVENT_CREATE = "event:create"
    EVENT_READ = "event:read"

    # Governance permissions
    GOVERNANCE_READ = "governance:read"
    GOVERNANCE_WRITE = "governance:write"
    GOVERNANCE_ADMIN = "governance:admin"

    # Graph permissions
    GRAPH_READ = "graph:read"
    GRAPH_WRITE = "graph:write"

    # Admin permissions
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"


# Role to Permission Mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.READONLY: {
        Permission.MEMORY_READ,
        Permission.EVENT_READ,
        Permission.GOVERNANCE_READ,
        Permission.GRAPH_READ,
    },
    UserRole.USER: {
        Permission.MEMORY_CREATE,
        Permission.MEMORY_READ,
        Permission.MEMORY_UPDATE,
        Permission.EVENT_CREATE,
        Permission.EVENT_READ,
        Permission.GOVERNANCE_READ,
        Permission.GRAPH_READ,
    },
    UserRole.ADMIN: {
        # Admin has all permissions
        Permission.MEMORY_CREATE,
        Permission.MEMORY_READ,
        Permission.MEMORY_UPDATE,
        Permission.MEMORY_DELETE,
        Permission.EVENT_CREATE,
        Permission.EVENT_READ,
        Permission.GOVERNANCE_READ,
        Permission.GOVERNANCE_WRITE,
        Permission.GOVERNANCE_ADMIN,
        Permission.GRAPH_READ,
        Permission.GRAPH_WRITE,
        Permission.USER_MANAGE,
        Permission.SYSTEM_CONFIG,
    },
    UserRole.SYSTEM: {
        # System user has all permissions (explicitly defined to avoid circular reference)
        Permission.MEMORY_CREATE,
        Permission.MEMORY_READ,
        Permission.MEMORY_UPDATE,
        Permission.MEMORY_DELETE,
        Permission.EVENT_CREATE,
        Permission.EVENT_READ,
        Permission.GOVERNANCE_READ,
        Permission.GOVERNANCE_WRITE,
        Permission.GOVERNANCE_ADMIN,
        Permission.GRAPH_READ,
        Permission.GRAPH_WRITE,
        Permission.USER_MANAGE,
        Permission.SYSTEM_CONFIG,
    },
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(role: UserRole, required_permission: Permission) -> bool:
    """Check if a role has a required permission (for use in code)."""
    return has_permission(role, required_permission)
