"""
Application-wide exception hierarchy.

Provides specific exception types for different error scenarios.
Replace generic ValueError/Exception with these for better error handling.
"""

from typing import Any


class MemoryXError(Exception):
    """Base exception for all MemoryX application errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(MemoryXError):
    """Raised when input validation fails."""

    pass


class NotFoundError(MemoryXError):
    """Raised when a requested resource is not found."""

    pass


class ConflictError(MemoryXError):
    """Raised when a conflict occurs (e.g., duplicate name)."""

    pass


class BusinessRuleError(MemoryXError):
    """Raised when a business rule is violated."""

    pass


class AuthenticationError(MemoryXError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(MemoryXError):
    """Raised when authorization fails (insufficient permissions)."""

    pass


class RateLimitError(MemoryXError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class GovernanceViolationError(MemoryXError):
    """Raised when a governance rule is violated."""

    def __init__(
        self,
        message: str,
        action: str,
        severity: str,
        triggered_rules: list[dict[str, Any]] | None = None
    ):
        super().__init__(message)
        self.action = action
        self.severity = severity
        self.triggered_rules = triggered_rules or []
