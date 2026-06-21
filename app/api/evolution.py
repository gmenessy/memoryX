"""
Evolution API Routes - REST Endpoints for Memory Evolution Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.evolution import MemoryPatchCreate, MemoryPatchResponse, MemoryEvolutionHistory, PATCH_TYPES, MEMORY_STATES
from app.services.evolution_service import EvolutionService

router = APIRouter(prefix="/api/evolution", tags=["Evolution"])


@router.post("/patch", response_model=MemoryPatchResponse, status_code=status.HTTP_201_CREATED)
async def create_patch(
    patch_data: MemoryPatchCreate,
    session: AsyncSession = Depends(get_db_session)
) -> MemoryPatchResponse:
    """
    Create a new memory patch.

    Patches track how memory evolves over time.
    Memory is never overwritten - it evolves through patches.

    - **target_memory**: Memory ID to patch
    - **patch_type**: Type of patch (update, merge, split, deprecate, archive, promotion)
    - **old_value**: Previous value/state
    - **new_value**: New value/state
    - **reason**: Reason for the patch
    - **confidence**: Confidence in this patch (0-1)
    """
    try:
        service = EvolutionService(session)
        return await service.create_patch(patch_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/patch/{patch_id}", response_model=MemoryPatchResponse)
async def get_patch(
    patch_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> MemoryPatchResponse:
    """
    Get a specific patch by ID.
    """
    service = EvolutionService(session)
    patch = await service.get_patch(patch_id)

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch {patch_id} not found"
        )

    return patch


@router.get("/patches", response_model=list[MemoryPatchResponse])
async def list_patches(
    patch_type: str | None = Query(None, description="Filter by patch type"),
    target_memory: UUID | None = Query(None, description="Filter by target memory"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[MemoryPatchResponse]:
    """
    List patches with optional filtering and pagination.

    Results are ordered by created_at (newest first).
    """
    service = EvolutionService(session)
    return await service.list_patches(
        patch_type=patch_type,
        target_memory=target_memory,
        limit=limit,
        offset=offset
    )


@router.get("/memory/{memory_id}/history", response_model=MemoryEvolutionHistory)
async def get_memory_history(
    memory_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> MemoryEvolutionHistory:
    """
    Get complete evolution history for a memory.

    Includes current state, all patches, and calculated fitness score.
    """
    try:
        service = EvolutionService(session)
        return await service.get_memory_evolution_history(memory_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/memory/{memory_id}/patches", response_model=list[MemoryPatchResponse])
async def get_memory_patches(
    memory_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    session: AsyncSession = Depends(get_db_session)
) -> list[MemoryPatchResponse]:
    """
    Get all patches for a specific memory.

    Shows the evolution history of the memory.
    """
    try:
        service = EvolutionService(session)
        return await service.get_patches_for_memory(memory_id, limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/memory/{memory_id}/promote", response_model=MemoryPatchResponse)
async def promote_memory(
    memory_id: UUID,
    reason: str = Query(..., min_length=1, description="Reason for promotion"),
    confidence: float = Query(0.8, ge=0.0, le=1.0, description="Confidence in promotion"),
    session: AsyncSession = Depends(get_db_session)
) -> MemoryPatchResponse:
    """
    Promote a memory (e.g., from candidate to active).

    Creates a promotion patch to track the state change.
    """
    try:
        service = EvolutionService(session)
        return await service.promote_memory(memory_id, reason, confidence)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/memory/{memory_id}/deprecate", response_model=MemoryPatchResponse)
async def deprecate_memory(
    memory_id: UUID,
    reason: str = Query(..., min_length=1, description="Reason for deprecation"),
    replacement_memory: UUID | None = Query(None, description="Optional replacement memory ID"),
    session: AsyncSession = Depends(get_db_session)
) -> MemoryPatchResponse:
    """
    Deprecate a memory.

    Creates a deprecation patch. Memory is kept for reference but marked as deprecated.
    """
    try:
        service = EvolutionService(session)
        return await service.deprecate_memory(memory_id, reason, replacement_memory)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/memories/merge", response_model=MemoryPatchResponse)
async def merge_memories(
    source_memories: list[UUID],
    target_memory: UUID,
    reason: str = Query(..., min_length=1, description="Reason for merge"),
    confidence: float = Query(0.7, ge=0.0, le=1.0, description="Confidence in merge quality"),
    session: AsyncSession = Depends(get_db_session)
) -> MemoryPatchResponse:
    """
    Merge multiple memories into one.

    Creates a merge patch tracking which memories were combined.
    The target memory will contain the merged result.
    """
    try:
        service = EvolutionService(session)
        return await service.merge_memories(source_memories, target_memory, reason, confidence)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/types", response_model=dict)
async def get_evolution_types() -> dict:
    """
    Get available patch types and memory states.

    Returns the valid patch types and memory states according to the specification.
    """
    return {
        "patch_types": PATCH_TYPES,
        "memory_states": MEMORY_STATES
    }


@router.get("/statistics", response_model=dict)
async def get_evolution_statistics(
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get evolution system statistics.

    Returns counts and breakdowns by patch type.
    """
    service = EvolutionService(session)
    return await service.get_evolution_statistics()


@router.get("/count", response_model=dict)
async def count_patches(
    patch_type: str | None = Query(None, description="Filter by patch type"),
    target_memory: UUID | None = Query(None, description="Filter by target memory"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Count patches matching filters.

    Returns the total count (useful for pagination).
    """
    service = EvolutionService(session)
    count = await service.count_patches(
        patch_type=patch_type,
        target_memory=target_memory
    )

    return {"count": count}