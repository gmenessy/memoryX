"""
Global Exception Handlers for FastAPI.

Provides consistent error responses across all API endpoints.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.config import settings
from app.exceptions import (
    MemoryXError,
    ValidationError,
    NotFoundError,
    ConflictError,
    BusinessRuleError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    GovernanceViolationError,
)
from app.logging_config import log_error


def create_error_response(
    status_code: int,
    message: str,
    error_type: str,
    details: dict | None = None,
) -> JSONResponse:
    """
    Create standardized error response (backward compatible).

    Args:
        status_code: HTTP status code
        message: Human-readable error message
        error_type: Type of error (e.g., "validation_error")
        details: Additional error details

    Returns:
        JSONResponse with standardized format
    """
    # Check for backward compatibility header
    # If client wants old format, use flat structure
    # For now, use nested format (new standard)

    content = {
        "error": {
            "type": error_type,
            "message": message,
        }
    }

    # Add details in debug mode or if explicitly provided
    if settings.debug or details:
        content["error"]["details"] = details or {}

    return JSONResponse(status_code=status_code, content=content)


async def memoryx_error_handler(request: Request, exc: MemoryXError) -> JSONResponse:
    """Handler for base MemoryXError and its subclasses."""
    log_error(
        context=f"{request.method} {request.url.path}",
        error=exc,
        path=request.url.path,
        method=request.method,
    )

    # Map exception types to status codes and error types
    error_mapping = {
        ValidationError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error"),
        NotFoundError: (status.HTTP_404_NOT_FOUND, "not_found"),
        ConflictError: (status.HTTP_409_CONFLICT, "conflict"),
        BusinessRuleError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "business_rule_error"),
        AuthenticationError: (status.HTTP_401_UNAUTHORIZED, "authentication_error"),
        AuthorizationError: (status.HTTP_403_FORBIDDEN, "authorization_error"),
        RateLimitError: (status.HTTP_429_TOO_MANY_REQUESTS, "rate_limit_error"),
        GovernanceViolationError: (status.HTTP_403_FORBIDDEN, "governance_violation"),
    }

    # Get status code and error type, default to 500
    status_code, error_type = error_mapping.get(
        type(exc),
        (status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error")
    )

    # Add retry-after for rate limit errors
    details = exc.details.copy()
    headers = {}
    if isinstance(exc, RateLimitError):
        if exc.retry_after:
            details["retry_after"] = exc.retry_after
            headers["Retry-After"] = str(exc.retry_after)
        else:
            # Default retry-after if not specified
            default_retry = 60
            details["retry_after"] = default_retry
            headers["Retry-After"] = str(default_retry)

    # Add governance-specific details
    if isinstance(exc, GovernanceViolationError):
        details.update({
            "action": exc.action,
            "severity": exc.severity,
            "triggered_rules": exc.triggered_rules,
        })

    response = create_error_response(
        status_code=status_code,
        message=exc.message,
        error_type=error_type,
        details=details,
    )

    # Add headers to the response
    if headers:
        response.headers.update(headers)

    return response


async def pydantic_validation_error_handler(
    request: Request,
    exc: PydanticValidationError,
) -> JSONResponse:
    """Handler for Pydantic validation errors."""
    log_error(
        context=f"Pydantic validation: {request.method} {request.url.path}",
        error=exc,
        path=request.url.path,
        method=request.method,
    )

    # Convert Pydantic errors to readable format
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed",
        error_type="validation_error",
        details={"fields": errors},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions."""
    log_error(
        context=f"Unhandled exception: {request.method} {request.url.path}",
        error=exc,
        path=request.url.path,
        method=request.method,
    )

    if settings.debug:
        # Show full error details in debug mode
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
            error_type="internal_error",
            details={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )
    else:
        # Hide details in production
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An internal error occurred",
            error_type="internal_error",
        )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(MemoryXError, memoryx_error_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
