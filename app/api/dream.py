"""
Dream API Routes - REST Endpoints for Dream Engine Operations

The Dream Engine provides asynchronous memory consolidation:
- Daydream: Event → Memory Transformation (running)
- Nightdream: Merge, Compress, Deduplicate (periodic)
- Deepdream: Pattern Discovery, Policy Discovery (strategic)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.dream import (
    DaydreamJob,
    DaydreamJobCreate,
    DaydreamJobResponse,
    NightdreamJob,
    NightdreamJobCreate,
    NightdreamJobResponse,
    DeepdreamJob,
    DeepdreamJobCreate,
    DeepdreamJobResponse,
    DREAM_TYPES,
    DREAM_STATUSES,
    TRANSFORMATION_TYPES,
    NIGHTDREAM_OPERATIONS,
    DEEPDREAM_OPERATIONS,
    ANALYSIS_DEPTHS,
)
from app.services.dream_service import DreamService

router = APIRouter(prefix="/api/dream", tags=["Dream Engine"])


# Daydream Endpoints


@router.post("/daydream/jobs", response_model=DaydreamJob, status_code=status.HTTP_201_CREATED)
async def create_daydream_job(
    job_data: DaydreamJobCreate,
    session: AsyncSession = Depends(get_db_session)
) -> DaydreamJob:
    """
    Create a new daydream job for Event → Memory transformation.

    Daydream runs continuously, transforming events into memories.

    Transformation types:
    - **direct**: Direct event to memory (one-to-one)
    - **aggregated**: Multiple events to single memory (many-to-one)
    - **extracted**: Extract key information (one-to-one, filtered)
    - **inferred**: Infer new knowledge (one-to-one, enhanced)

    - **source_events**: List of event IDs to transform
    - **transformation_type**: Type of transformation
    - **processing_params**: Optional processing parameters
    - **priority**: Job priority (0-1, higher processed first)
    """
    try:
        service = DreamService(session)
        return await service.create_daydream_job(job_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/daydream/jobs/{job_id}", response_model=DaydreamJob)
async def get_daydream_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> DaydreamJob:
    """Get a daydream job by ID."""
    service = DreamService(session)
    job = await service.get_daydream_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daydream job {job_id} not found"
        )

    return job


@router.get("/daydream/jobs", response_model=list[DaydreamJob])
async def list_daydream_jobs(
    status: str | None = Query(None, description="Filter by status"),
    transformation_type: str | None = Query(None, description="Filter by transformation type"),
    priority_min: float | None = Query(None, description="Minimum priority"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[DaydreamJob]:
    """
    List daydream jobs with optional filtering.

    Results are ordered by priority (highest first) then creation date.
    """
    service = DreamService(session)
    return await service.list_daydream_jobs(status, transformation_type, priority_min, limit, offset)


@router.post("/daydream/jobs/{job_id}/process", response_model=DaydreamJob)
async def process_daydream_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session)
) -> DaydreamJob:
    """
    Process a daydream job - transform events into memory.

    This is the CORE Daydream endpoint.
    It performs the Event → Memory transformation.

    The job will be processed asynchronously in the background.
    """
    service = DreamService(session)

    # Verify job exists
    job = await service.get_daydream_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daydream job {job_id} not found"
        )

    # Process in background
    background_tasks.add_task(service.process_daydream_job, job_id)

    return job


@router.delete("/daydream/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daydream_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """Delete a daydream job by ID."""
    service = DreamService(session)
    success = await service.delete_daydream_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daydream job {job_id} not found"
        )


@router.get("/daydream/jobs/count", response_model=dict)
async def count_daydream_jobs(
    status: str | None = Query(None, description="Filter by status"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Count daydream jobs matching filters."""
    service = DreamService(session)
    count = await service.count_daydream_jobs(status)
    return {"count": count}


@router.get("/daydream/jobs/pending", response_model=list[DaydreamJob])
async def get_pending_daydream_jobs(
    limit: int = Query(50, ge=1, le=500, description="Max results (1-500)"),
    session: AsyncSession = Depends(get_db_session)
) -> list[DaydreamJob]:
    """
    Get pending daydream jobs for processing.

    Returns jobs ordered by priority (highest first).
    """
    service = DreamService(session)
    return await service.get_pending_daydream_jobs(limit)


# Nightdream Endpoints


@router.post("/nightdream/jobs", response_model=NightdreamJob, status_code=status.HTTP_201_CREATED)
async def create_nightdream_job(
    job_data: NightdreamJobCreate,
    session: AsyncSession = Depends(get_db_session)
) -> NightdreamJob:
    """
    Create a new nightdream job for periodic consolidation.

    Nightdream operations:
    - **merge**: Merge multiple memories
    - **compress**: Compress memory content
    - **deduplicate**: Remove duplicate memories

    - **operation**: Type of consolidation operation
    - **scope**: Operation scope
    - **target_memories**: Memory IDs to process
    - **processing_params**: Optional processing parameters
    - **scheduled_for**: Schedule for specific time (optional)
    """
    try:
        service = DreamService(session)
        return await service.create_nightdream_job(job_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/nightdream/jobs/{job_id}", response_model=NightdreamJob)
async def get_nightdream_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> NightdreamJob:
    """Get a nightdream job by ID."""
    service = DreamService(session)
    job = await service.get_nightdream_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nightdream job {job_id} not found"
        )

    return job


@router.get("/nightdream/jobs", response_model=list[NightdreamJob])
async def list_nightdream_jobs(
    status: str | None = Query(None, description="Filter by status"),
    operation: str | None = Query(None, description="Filter by operation"),
    scope: str | None = Query(None, description="Filter by scope"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[NightdreamJob]:
    """List nightdream jobs with optional filtering."""
    service = DreamService(session)
    return await service.list_nightdream_jobs(status, operation, scope, limit, offset)


@router.delete("/nightdream/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nightdream_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """Delete a nightdream job by ID."""
    service = DreamService(session)
    success = await service.delete_nightdream_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nightdream job {job_id} not found"
        )


@router.get("/nightdream/jobs/count", response_model=dict)
async def count_nightdream_jobs(
    status: str | None = Query(None, description="Filter by status"),
    operation: str | None = Query(None, description="Filter by operation"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Count nightdream jobs matching filters."""
    service = DreamService(session)
    count = await service.count_nightdream_jobs(status, operation)
    return {"count": count}


@router.get("/nightdream/jobs/scheduled", response_model=list[NightdreamJob])
async def get_scheduled_nightdream_jobs(
    limit: int = Query(50, ge=1, le=500, description="Max results (1-500)"),
    session: AsyncSession = Depends(get_db_session)
) -> list[NightdreamJob]:
    """
    Get scheduled nightdream jobs that are due.

    Returns jobs that are ready to be processed.
    """
    service = DreamService(session)
    return await service.get_scheduled_nightdream_jobs(limit)


# Deepdream Endpoints


@router.post("/deepdream/jobs", response_model=DeepdreamJob, status_code=status.HTTP_201_CREATED)
async def create_deepdream_job(
    job_data: DeepdreamJobCreate,
    session: AsyncSession = Depends(get_db_session)
) -> DeepdreamJob:
    """
    Create a new deepdream job for strategic analysis.

    Deepdream operations:
    - **pattern_discovery**: Discover patterns in memory
    - **policy_discovery**: Suggest new governance policies
    - **dna_evolution**: Evolve memory system DNA

    - **operation**: Type of analysis operation
    - **scope**: Analysis scope
    - **analysis_depth**: Analysis depth (quick, standard, deep)
    - **processing_params**: Optional processing parameters
    """
    try:
        service = DreamService(session)
        return await service.create_deepdream_job(job_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/deepdream/jobs/{job_id}", response_model=DeepdreamJob)
async def get_deepdream_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> DeepdreamJob:
    """Get a deepdream job by ID."""
    service = DreamService(session)
    job = await service.get_deepdream_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deepdream job {job_id} not found"
        )

    return job


@router.get("/deepdream/jobs", response_model=list[DeepdreamJob])
async def list_deepdream_jobs(
    status: str | None = Query(None, description="Filter by status"),
    operation: str | None = Query(None, description="Filter by operation"),
    scope: str | None = Query(None, description="Filter by scope"),
    analysis_depth: str | None = Query(None, description="Filter by analysis depth"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[DeepdreamJob]:
    """List deepdream jobs with optional filtering."""
    service = DreamService(session)
    return await service.list_deepdream_jobs(status, operation, scope, analysis_depth, limit, offset)


@router.delete("/deepdream/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deepdream_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """Delete a deepdream job by ID."""
    service = DreamService(session)
    success = await service.delete_deepdream_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deepdream job {job_id} not found"
        )


@router.get("/deepdream/jobs/count", response_model=dict)
async def count_deepdream_jobs(
    status: str | None = Query(None, description="Filter by status"),
    operation: str | None = Query(None, description="Filter by operation"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """Count deepdream jobs matching filters."""
    service = DreamService(session)
    count = await service.count_deepdream_jobs(status, operation)
    return {"count": count}


# Statistics Endpoints


@router.get("/statistics", response_model=dict)
async def get_dream_statistics(
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get dream engine statistics.

    Returns statistics for all dream types:
    - **daydream**: Event → Memory transformation stats
    - **nightdream**: Consolidation operation stats
    - **deepdream**: Analysis operation stats

    Each includes:
    - **total**: Total jobs
    - **pending**: Pending jobs
    - **running**: Running jobs
    - **completed**: Completed jobs
    - **failed**: Failed jobs
    """
    service = DreamService(session)
    return await service.get_statistics()


# Metadata Endpoints


@router.get("/types", response_model=dict)
async def get_dream_types() -> dict:
    """
    Get available types for Dream Engine.

    Returns:
    - **dream_types**: Available dream types
    - **statuses**: Available job statuses
    - **transformation_types**: Available daydream transformation types
    - **nightdream_operations**: Available nightdream operations
    - **deepdream_operations**: Available deepdream operations
    - **analysis_depths**: Available analysis depths
    """
    return {
        "dream_types": DREAM_TYPES,
        "statuses": DREAM_STATUSES,
        "transformation_types": TRANSFORMATION_TYPES,
        "nightdream_operations": NIGHTDREAM_OPERATIONS,
        "deepdream_operations": DEEPDREAM_OPERATIONS,
        "analysis_depths": ANALYSIS_DEPTHS
    }
