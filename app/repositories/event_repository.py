"""
Event Repository - Data Access Layer for Events
"""
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventDB, EventCreate, EventResponse


class EventRepository:
    """
    Repository for Event operations.
    Enforces append-only principle - no update or delete operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, event_data: EventCreate) -> EventResponse:
        """
        Create a new event. This is the ONLY way to add events.

        Args:
            event_data: Event creation data

        Returns:
            Created event response
        """
        event_db = EventDB(
            event_id=event_data.event_id if event_data.event_id else None,
            timestamp=event_data.timestamp if hasattr(event_data, 'timestamp') else datetime.utcnow(),
            event_type=event_data.event_type,
            actor=event_data.actor,
            scope=event_data.scope,
            payload=event_data.payload,
            metadata=event_data.metadata
        )

        self.session.add(event_db)
        await self.session.flush()
        await self.session.refresh(event_db)

        return EventResponse(
            event_id=event_db.event_id,
            timestamp=event_db.timestamp,
            event_type=event_db.event_type,
            actor=event_db.actor,
            scope=event_db.scope,
            payload=event_db.payload,
            metadata=event_db.metadata
        )

    async def get_by_id(self, event_id: UUID) -> EventResponse | None:
        """
        Get event by ID. Events are immutable and never deleted.

        Args:
            event_id: Event UUID

        Returns:
            Event response or None if not found
        """
        result = await self.session.execute(
            select(EventDB).where(EventDB.event_id == event_id)
        )
        event_db = result.scalar_one_or_none()

        if not event_db:
            return None

        return EventResponse(
            event_id=event_db.event_id,
            timestamp=event_db.timestamp,
            event_type=event_db.event_type,
            actor=event_db.actor,
            scope=event_db.scope,
            payload=event_db.payload,
            metadata=event_db.metadata
        )

    async def list_events(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        scope: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[EventResponse]:
        """
        List events with optional filtering.
        Implements pagination for large result sets.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            scope: Filter by scope
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of events matching filters
        """
        query = select(EventDB)

        # Apply filters
        conditions = []
        if event_type:
            conditions.append(EventDB.event_type == event_type)
        if actor:
            conditions.append(EventDB.actor == actor)
        if scope:
            conditions.append(EventDB.scope == scope)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by timestamp descending (newest first)
        query = query.order_by(EventDB.timestamp.desc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        events = result.scalars().all()

        return [
            EventResponse(
                event_id=event.event_id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                actor=event.actor,
                scope=event.scope,
                payload=event.payload,
                metadata=event.metadata
            )
            for event in events
        ]

    async def stream_events(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        scope: str | None = None,
        batch_size: int = 100
    ) -> AsyncIterator[EventResponse]:
        """
        Stream events efficiently for large datasets.
        Useful for exports, analytics, and batch processing.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            scope: Filter by scope
            batch_size: Number of events per batch

        Yields:
            Event responses one by one
        """
        offset = 0

        while True:
            events = await self.list_events(
                event_type=event_type,
                actor=actor,
                scope=scope,
                limit=batch_size,
                offset=offset
            )

            if not events:
                break

            for event in events:
                yield event

            offset += batch_size

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
            Number of matching events
        """
        from sqlalchemy import func, and_

        query = select(func.count(EventDB.event_id))

        conditions = []
        if event_type:
            conditions.append(EventDB.event_type == event_type)
        if actor:
            conditions.append(EventDB.actor == actor)
        if scope:
            conditions.append(EventDB.scope == scope)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0