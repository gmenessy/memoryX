"""
Event Service - Business Logic Layer for Events
"""
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger, log_service_action, log_error
from app.models.event import EventCreate, EventResponse, EVENT_TYPES
from app.repositories.event_repository import EventRepository

logger = get_logger(__name__)


class EventService:
    """
    Service layer for Event operations.
    Handles business logic and validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = EventRepository(session)

    async def create_event(self, event_data: EventCreate) -> EventResponse:
        """
        Create a new event with validation.

        Args:
            event_data: Event creation data

        Returns:
            Created event response

        Raises:
            ValueError: If event type is invalid
        """
        logger.info(f"Creating event: {event_data.event_type} by {event_data.actor}")

        try:
            # Validate event type
            if event_data.event_type not in EVENT_TYPES:
                raise ValueError(
                    f"Invalid event type: {event_data.event_type}. "
                    f"Must be one of: {', '.join(EVENT_TYPES)}"
                )

            # Validate required fields
            if not event_data.actor:
                raise ValueError("Actor is required")

            if not event_data.scope:
                raise ValueError("Scope is required")

            # Create event via repository
            result = await self.repository.create(event_data)
            log_service_action("EventService", "create_event", event_id=str(result.id), event_type=event_data.event_type)
            return result

        except Exception as e:
            log_error("EventService.create_event", e, event_type=event_data.event_type, actor=event_data.actor)
            raise

    async def get_event(self, event_id: UUID) -> EventResponse | None:
        """
        Get event by ID.

        Args:
            event_id: Event UUID

        Returns:
            Event response or None
        """
        return await self.repository.get_by_id(event_id)

    async def list_events(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        scope: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[EventResponse]:
        """
        List events with filtering and pagination.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            scope: Filter by scope
            limit: Max results
            offset: Pagination offset

        Returns:
            List of events
        """
        # Validate limit
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.repository.list_events(
            event_type=event_type,
            actor=actor,
            scope=scope,
            limit=limit,
            offset=offset
        )

    async def stream_events(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        scope: str | None = None,
        batch_size: int = 100
    ) -> AsyncIterator[EventResponse]:
        """
        Stream events for large datasets.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            scope: Filter by scope
            batch_size: Batch size for streaming

        Yields:
            Event responses
        """
        async for event in self.repository.stream_events(
            event_type=event_type,
            actor=actor,
            scope=scope,
            batch_size=batch_size
        ):
            yield event

    async def count_events(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        scope: str | None = None
    ) -> int:
        """
        Count events matching filters.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            scope: Filter by scope

        Returns:
            Event count
        """
        return await self.repository.count_events(
            event_type=event_type,
            actor=actor,
            scope=scope
        )

    async def get_event_statistics(
        self,
        scope: str | None = None
    ) -> dict:
        """
        Get statistics about events.

        Args:
            scope: Filter by scope

        Returns:
            Statistics dictionary
        """
        total_count = await self.count_events(scope=scope)

        # Count by event type
        event_type_counts = {}
        for event_type in EVENT_TYPES:
            count = await self.count_events(
                event_type=event_type,
                scope=scope
            )
            event_type_counts[event_type] = count

        return {
            "total_events": total_count,
            "by_event_type": event_type_counts,
            "scope": scope or "all"
        }