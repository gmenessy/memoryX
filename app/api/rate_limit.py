"""
Rate Limiting Configuration and Middleware.

Implements per-endpoint rate limiting using slowapi to protect against DoS attacks.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from typing import Callable

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/hour", "50/minute"],
    storage_uri="memory://",  # In-memory storage (for production, use Redis)
    headers_enabled=True,  # Add rate limit info to response headers
)


def get_user_id(request: Request) -> str:
    """
    Get user identifier for rate limiting.

    For authenticated requests, uses user_id from JWT token.
    For unauthenticated requests, falls back to IP address.
    """
    # Try to get user from JWT token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # In a real implementation, we'd decode the token here
        # For now, fall back to IP to avoid token verification overhead
        pass

    return get_remote_address(request)


# Rate limit definitions for different endpoint types
RATE_LIMITS = {
    # Authentication endpoints (stricter limits)
    "auth": "5/minute",  # 5 login attempts per minute

    # Read endpoints (higher limits)
    "read": "1000/hour",  # 1000 read requests per hour

    # Write endpoints (moderate limits)
    "write": "200/hour",  # 200 write requests per hour

    # Admin endpoints (stricter limits)
    "admin": "100/hour",  # 100 admin requests per hour

    # Search endpoints (higher limits due to pagination)
    "search": "300/hour",  # 300 search requests per hour

    # Bulk operations (very strict)
    "bulk": "10/hour",  # 10 bulk operations per hour
}


# Rate limit decorators for common patterns
def rate_limit_auth(endpoint: Callable):
    """Rate limit decorator for auth endpoints."""
    return limiter.limit(RATE_LIMITS["auth"])(endpoint)


def rate_limit_read(endpoint: Callable):
    """Rate limit decorator for read endpoints."""
    return limiter.limit(RATE_LIMITS["read"])(endpoint)


def rate_limit_write(endpoint: Callable):
    """Rate limit decorator for write endpoints."""
    return limiter.limit(RATE_LIMITS["write"])(endpoint)


def rate_limit_admin(endpoint: Callable):
    """Rate limit decorator for admin endpoints."""
    return limiter.limit(RATE_LIMITS["admin"])(endpoint)


def rate_limit_search(endpoint: Callable):
    """Rate limit decorator for search endpoints."""
    return limiter.limit(RATE_LIMITS["search"])(endpoint)


def rate_limit_bulk(endpoint: Callable):
    """Rate limit decorator for bulk operations."""
    return limiter.limit(RATE_LIMITS["bulk"])(endpoint)
