"""
Logging Configuration and Utilities.

Provides structured logging for the application with JSON output for production.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger as loguru_logger

from app.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.moduleName,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging() -> None:
    """
    Configure logging for the application.

    Sets up structured logging with JSON output for production
    and readable text output for development.
    """
    # Remove default handlers
    loguru_logger.remove()

    # Console handler with formatting
    if settings.debug:
        # Development: readable text format
        loguru_logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.log_level,
            colorize=True,
        )
    else:
        # Production: JSON format
        loguru_logger.add(
            sys.stderr,
            format="{message}",
            level=settings.log_level,
            serialize=True,  # JSON output
        )

    # File handler for persistent logging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    loguru_logger.add(
        log_dir / "app.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.log_level,
        serialize=not settings.debug,  # JSON in production
    )

    loguru_logger.info("Logging configured successfully")


def get_logger(name: str) -> Any:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return loguru_logger.bind(logger=name)


# Convenience logging functions for common patterns

def log_auth_event(event_type: str, **kwargs) -> None:
    """
    Log authentication-related events.

    Args:
        event_type: Type of auth event (login, logout, register, etc.)
        **kwargs: Additional event data
    """
    loguru_logger.bind(event_type="auth").info(
        f"Auth event: {event_type}",
        extra={"auth_event": event_type, **kwargs}
    )


def log_governance_action(action: str, **kwargs) -> None:
    """
    Log governance-related actions for audit trail.

    Args:
        action: Governance action performed
        **kwargs: Additional action data
    """
    loguru_logger.bind(event_type="governance").info(
        f"Governance action: {action}",
        extra={"governance_action": action, **kwargs}
    )


def log_service_action(service: str, action: str, **kwargs) -> None:
    """
    Log service-related actions.

    Args:
        service: Service name
        action: Action performed
        **kwargs: Additional action data
    """
    loguru_logger.bind(event_type="service").info(
        f"{service} - {action}",
        extra={"service": service, "action": action, **kwargs}
    )


def log_error(context: str, error: Exception, **kwargs) -> None:
    """
    Log error with context and stack trace.

    Args:
        context: Error context
        error: Exception instance
        **kwargs: Additional error data
    """
    # Log with stack trace (exc_info=True equivalent)
    loguru_logger.opt(
        exception=error
    ).bind(
        event_type="error"
    ).error(
        f"Error in {context}: {str(error)}",
        extra={
            "context": context,
            "error_type": type(error).__name__,
            **kwargs
        }
    )
