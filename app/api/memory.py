"""
Memory API Routes - REST Endpoints for Memory Card Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.memory import MemoryCardCreate, MemoryCardUpdate, MemoryCardResponse, MEMORY_TYPES
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/memory", tags=["Memory"])


@router.post("/", response_model=MemoryCardResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory_data: MemoryCardCreate,
    session: AsyncSession = Depends(get_db_session)
) -> MemoryCardResponse:
    """
    Create a new memory card.

    Memory cards store typed information in the system.
    Each memory card has a type (episodic, semantic, procedural, etc.)
    and can reference source events.

    - **memory_type**: Type of memory (episodic, semantic, procedural, etc.)
    - **title**: Memory title
    - **content**: Memory content
    - **confidence**: Confidence score (0-1)
    - **scope**: Scope/context (case_id, session_id, global)
    - **source_events**: List of source event IDs
    """
    try:
        service = MemoryService(session)
        return await service.create_memory(memory_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=list[MemoryCardResponse])
async def list_memories(
    memory_type: str | None = Query(None, description="Filter by memory type"),
    scope: str | None = Query(None, description="Filter by scope"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[MemoryCardResponse]:
    """
    List memory cards with optional filtering and pagination.

    Results are ordered by updated_at (most recently updated first).
    """
    service = MemoryService(session)
    return await service.list_memories(
        memory_type=memory_type,
        scope=scope,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset
    )


@router.get("/search", response_model=list[MemoryCardResponse])
async def search_memories(
    query: str = Query(..., min_length=1, description="Search query"),
    memory_type: str | None = Query(None, description="Filter by memory type"),
    scope: str | None = Query(None, description="Filter by scope"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    session: AsyncSession = Depends(get_db_session)
) -> list[MemoryCardResponse]:
    """
    Search memory cards by title and content.

    Uses case-insensitive substring matching.
    Results are ordered by updated_at (most recently updated first).
    """
    try:
        service = MemoryService(session)
        return await service.search_memories(
            query=query,
            memory_type=memory_type,
            scope=scope,
            limit=limit
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/types", response_model=list[str])
async def list_memory_types() -> list[str]:
    """
    Get available memory types.

    Returns the list of valid memory types according to the specification.
    """
    return MEMORY_TYPES


@router.get("/statistics", response_model=dict)
async def get_memory_statistics(
    scope: str | None = Query(None, description="Filter by scope"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get memory card statistics.

    Returns counts and breakdowns by memory type.
    """
    service = MemoryService(session)
    return await service.get_memory_statistics(scope=scope)


@router.get("/event/{event_id}", response_model=list[MemoryCardResponse])
async def get_memories_by_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> list[MemoryCardResponse]:
    """
    Get all memory cards derived from a specific event.

    Useful for tracing the origin of memories and understanding
    how events were processed into memories.
    """
    service = MemoryService(session)
    return await service.get_by_source_event(event_id)


@router.get("/{memory_id}", response_model=MemoryCardResponse)
async def get_memory(
    memory_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> MemoryCardResponse:
    """
    Get a specific memory card by ID.
    """
    service = MemoryService(session)
    memory = await service.get_memory(memory_id)

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found"
        )

    return memory


@router.put("/{memory_id}", response_model=MemoryCardResponse)
async def update_memory(
    memory_id: UUID,
    update_data: MemoryCardUpdate,
    session: AsyncSession = Depends(get_db_session)
) -> MemoryCardResponse:
    """
    Update a memory card.

    Updates create new versions (evolution system).
    Only provided fields are updated (partial update).
    """
    try:
        service = MemoryService(session)
        memory = await service.update_memory(memory_id, update_data)

        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found"
            )

        return memory
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/count", response_model=dict)
async def count_memories(
    memory_type: str | None = Query(None, description="Filter by memory type"),
    scope: str | None = Query(None, description="Filter by scope"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Count memory cards matching filters.

    Returns the total count (useful for pagination).
    """
    service = MemoryService(session)
    count = await service.count_memories(
        memory_type=memory_type,
        scope=scope
    )

    return {"count": count}