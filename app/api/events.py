"""
Event API Routes - REST Endpoints for Event Operations
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.event import EventCreate, EventResponse, EVENT_TYPES
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    session: AsyncSession = Depends(get_db_session)
) -> EventResponse:
    """
    Create a new event.

    Events are append-only - they cannot be modified or deleted.
    This is the foundation of the truth layer for the entire system.

    - **event_type**: Type of event (user_input, agent_action, tool_call, etc.)
    - **actor**: Who triggered the event (user ID, agent ID, system)
    - **scope**: Scope/context (case_id, session_id, global)
    - **payload**: Event data payload
    - **metadata**: Additional metadata
    """
    try:
        service = EventService(session)
        return await service.create_event(event_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=list[EventResponse])
async def list_events(
    event_type: str | None = Query(None, description="Filter by event type"),
    actor: str | None = Query(None, description="Filter by actor"),
    scope: str | None = Query(None, description="Filter by scope"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[EventResponse]:
    """
    List events with optional filtering and pagination.

    Results are ordered by timestamp (newest first).
    Use streaming endpoint for large datasets.
    """
    service = EventService(session)
    return await service.list_events(
        event_type=event_type,
        actor=actor,
        scope=scope,
        limit=limit,
        offset=offset
    )


@router.get("/types", response_model=list[str])
async def list_event_types() -> list[str]:
    """
    Get available event types.

    Returns the list of valid event types according to the specification.
    """
    return EVENT_TYPES


@router.get("/statistics", response_model=dict)
async def get_event_statistics(
    scope: str | None = Query(None, description="Filter by scope"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get event statistics.

    Returns counts and breakdowns by event type.
    """
    service = EventService(session)
    return await service.get_event_statistics(scope=scope)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> EventResponse:
    """
    Get a specific event by ID.

    Events are immutable and never deleted.
    """
    service = EventService(session)
    event = await service.get_event(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )

    return event


@router.get("/count", response_model=dict)
async def count_events(
    event_type: str | None = Query(None, description="Filter by event type"),
    actor: str | None = Query(None, description="Filter by actor"),
    scope: str | None = Query(None, description="Filter by scope"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Count events matching filters.

    Returns the total count (useful for pagination).
    """
    service = EventService(session)
    count = await service.count_events(
        event_type=event_type,
        actor=actor,
        scope=scope
    )

    return {"count": count}