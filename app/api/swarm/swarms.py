"""
Swarm API Routes - REST Endpoints for Swarm Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.swarm.models.swarm import (
    SwarmCreate,
    SwarmResponse,
    SwarmState,
    SwarmStatus,
    SwarmType,
    SwarmUpdate,
)
from app.swarm.services.swarm_service import SwarmService

router = APIRouter(prefix="/api/swarm/swarms", tags=["Swarm: Swarms"])


@router.post("/", response_model=SwarmResponse, status_code=status.HTTP_201_CREATED)
async def create_swarm(
    swarm_data: SwarmCreate,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Create a new swarm.

    Swarms are collections of agents that work together on tasks.
    """
    try:
        service = SwarmService(session)
        return await service.create_swarm(swarm_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=list[SwarmResponse])
async def list_swarms(
    swarm_type: SwarmType | None = Query(None, description="Filter by swarm type"),
    state: SwarmState | None = Query(None, description="Filter by state"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[SwarmResponse]:
    """
    List swarms with optional filtering and pagination.

    Results are ordered by creation time (newest first).
    """
    service = SwarmService(session)
    return await service.list_swarms(
        swarm_type=swarm_type,
        state=state,
        limit=limit,
        offset=offset
    )


@router.get("/{swarm_id}", response_model=SwarmResponse)
async def get_swarm(
    swarm_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Get a specific swarm by ID.
    """
    service = SwarmService(session)
    swarm = await service.get_swarm(swarm_id)
    if not swarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return swarm


@router.put("/{swarm_id}", response_model=SwarmResponse)
async def update_swarm(
    swarm_id: UUID,
    swarm_data: SwarmUpdate,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Update swarm properties.
    """
    service = SwarmService(session)
    swarm = await service.update_swarm(swarm_id, swarm_data)
    if not swarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return swarm


@router.post("/{swarm_id}/start", response_model=SwarmResponse)
async def start_swarm(
    swarm_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Start a swarm.

    Transitions the swarm to RUNNING state and activates all agents.
    """
    service = SwarmService(session)
    swarm = await service.start_swarm(swarm_id)
    if not swarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return swarm


@router.post("/{swarm_id}/pause", response_model=SwarmResponse)
async def pause_swarm(
    swarm_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Pause a swarm.

    Transitions the swarm to PAUSED state and pauses all agents.
    """
    service = SwarmService(session)
    swarm = await service.pause_swarm(swarm_id)
    if not swarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return swarm


@router.post("/{swarm_id}/resume", response_model=SwarmResponse)
async def resume_swarm(
    swarm_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Resume a paused swarm.

    Transitions the swarm back to RUNNING state.
    """
    service = SwarmService(session)
    swarm = await service.resume_swarm(swarm_id)
    if not swarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return swarm


@router.post("/{swarm_id}/terminate", response_model=SwarmResponse)
async def terminate_swarm(
    swarm_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Terminate a swarm.

    Transitions the swarm to TERMINATED state and stops all agents.
    """
    service = SwarmService(session)
    swarm = await service.terminate_swarm(swarm_id)
    if not swarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return swarm


@router.get("/{swarm_id}/status", response_model=SwarmStatus)
async def get_swarm_status(
    swarm_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmStatus:
    """
    Get detailed swarm status.

    Includes agent states, task statistics, and uptime.
    """
    service = SwarmService(session)
    status_data = await service.get_swarm_status(swarm_id)
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return status_data


@router.post("/{swarm_id}/agents/{agent_id}", response_model=SwarmResponse)
async def add_agent_to_swarm(
    swarm_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Add an agent to a swarm.
    """
    try:
        service = SwarmService(session)
        swarm = await service.add_agent(swarm_id, agent_id)
        if not swarm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Swarm {swarm_id} not found"
            )
        return swarm
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{swarm_id}/agents/{agent_id}", response_model=SwarmResponse)
async def remove_agent_from_swarm(
    swarm_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> SwarmResponse:
    """
    Remove an agent from a swarm.
    """
    service = SwarmService(session)
    swarm = await service.remove_agent(swarm_id, agent_id)
    if not swarm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
    return swarm


@router.delete("/{swarm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_swarm(
    swarm_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Delete a swarm.

    Permanently removes the swarm and all its agents.
    """
    service = SwarmService(session)
    success = await service.delete_swarm(swarm_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm {swarm_id} not found"
        )
