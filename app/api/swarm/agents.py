"""
Agent API Routes - REST Endpoints for Agent Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.swarm.models.agent import (
    AgentCreate,
    AgentHeartbeat,
    AgentResponse,
    AgentState,
    AgentType,
    AgentUpdate,
)
from app.swarm.services.agent_service import AgentService

router = APIRouter(prefix="/api/swarm/agents", tags=["Swarm: Agents"])


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    session: AsyncSession = Depends(get_db_session)
) -> AgentResponse:
    """
    Create a new agent.

    Agents are autonomous units that can execute tasks within a swarm.
    Each agent has a type, capabilities, and configuration.
    """
    try:
        service = AgentService(session)
        return await service.create_agent(agent_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    agent_type: AgentType | None = Query(None, description="Filter by agent type"),
    state: AgentState | None = Query(None, description="Filter by state"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[AgentResponse]:
    """
    List agents with optional filtering and pagination.

    Results are ordered by creation time (newest first).
    """
    service = AgentService(session)
    return await service.list_agents(
        agent_type=agent_type,
        state=state,
        limit=limit,
        offset=offset
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> AgentResponse:
    """
    Get a specific agent by ID.
    """
    service = AgentService(session)
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    session: AsyncSession = Depends(get_db_session)
) -> AgentResponse:
    """
    Update agent properties.
    """
    service = AgentService(session)
    agent = await service.update_agent(agent_id, agent_data)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.post("/{agent_id}/start", response_model=AgentResponse)
async def start_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> AgentResponse:
    """
    Start an agent.

    Transitions the agent to ACTIVE state.
    """
    service = AgentService(session)
    agent = await service.start_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.post("/{agent_id}/pause", response_model=AgentResponse)
async def pause_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> AgentResponse:
    """
    Pause an agent.

    Transitions the agent to PAUSED state.
    """
    service = AgentService(session)
    agent = await service.pause_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.post("/{agent_id}/resume", response_model=AgentResponse)
async def resume_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> AgentResponse:
    """
    Resume a paused agent.

    Transitions the agent back to ACTIVE state.
    """
    service = AgentService(session)
    agent = await service.resume_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.post("/{agent_id}/heartbeat", response_model=AgentResponse)
async def agent_heartbeat(
    agent_id: UUID,
    heartbeat: AgentHeartbeat,
    session: AsyncSession = Depends(get_db_session)
) -> AgentResponse:
    """
    Register agent heartbeat.

    Updates the agent's last heartbeat timestamp and current state.
    """
    # Ensure heartbeat.agent_id matches path parameter
    if heartbeat.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Heartbeat agent_id must match path parameter"
        )

    service = AgentService(session)
    agent = await service.register_heartbeat(heartbeat)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.get("/{agent_id}/status", response_model=dict)
async def get_agent_status(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get detailed agent status including metrics.
    """
    service = AgentService(session)
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    metrics = await service.get_agent_metrics(agent_id)
    return {
        "agent": agent.model_dump(),
        "metrics": metrics.model_dump() if metrics else {}
    }


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Delete an agent.

    Permanently removes the agent from the system.
    """
    service = AgentService(session)
    success = await service.delete_agent(agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
