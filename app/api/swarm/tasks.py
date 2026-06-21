"""
Task API Routes - REST Endpoints for Task Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.swarm.models.task import (
    TaskCreate,
    TaskResponse,
    TaskSearchParams,
    TaskState,
    TaskType,
)
from app.swarm.services.task_service import TaskService

router = APIRouter(prefix="/api/swarm/tasks", tags=["Swarm: Tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    session: AsyncSession = Depends(get_db_session)
) -> TaskResponse:
    """
    Create a new task.

    Tasks are units of work distributed to agents within a swarm.
    """
    try:
        service = TaskService(session)
        return await service.create_task(task_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    swarm_id: UUID | None = Query(None, description="Filter by swarm ID"),
    assigned_agent_id: UUID | None = Query(None, description="Filter by assigned agent"),
    task_type: TaskType | None = Query(None, description="Filter by task type"),
    state: TaskState | None = Query(None, description="Filter by state"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[TaskResponse]:
    """
    List tasks with optional filtering and pagination.

    Results are ordered by priority (highest first) then creation time.
    """
    service = TaskService(session)
    search_params = TaskSearchParams(
        swarm_id=swarm_id,
        assigned_agent_id=assigned_agent_id,
        task_type=task_type,
        state=state,
        limit=limit,
        offset=offset
    )
    return await service.list_tasks(search_params)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> TaskResponse:
    """
    Get a specific task by ID.
    """
    service = TaskService(session)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task


@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: UUID,
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> TaskResponse:
    """
    Assign a task to an agent.
    """
    try:
        service = TaskService(session)
        task = await service.assign_task(task_id, agent_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    agent_id: UUID,
    result: dict,
    session: AsyncSession = Depends(get_db_session)
) -> TaskResponse:
    """
    Mark a task as completed with result.

    The agent must be assigned to the task.
    """
    try:
        service = TaskService(session)
        task = await service.complete_task(task_id, agent_id, result)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/fail", response_model=TaskResponse)
async def fail_task(
    task_id: UUID,
    agent_id: UUID,
    error: str,
    session: AsyncSession = Depends(get_db_session)
) -> TaskResponse:
    """
    Mark a task as failed.

    The task will be retried if retries are available.
    """
    try:
        service = TaskService(session)
        task = await service.fail_task(task_id, agent_id, error)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> TaskResponse:
    """
    Cancel a task.
    """
    service = TaskService(session)
    task = await service.cancel_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task


@router.get("/{swarm_id}/queue", response_model=list[TaskResponse])
async def get_swarm_task_queue(
    swarm_id: UUID,
    limit: int = Query(10, ge=1, le=100, description="Max tasks to return"),
    session: AsyncSession = Depends(get_db_session)
) -> list[TaskResponse]:
    """
    Get next pending tasks for a swarm.

    Returns high-priority pending tasks that can be assigned to agents.
    """
    service = TaskService(session)
    return await service.get_next_task(swarm_id, limit=limit)


@router.get("/agent/{agent_id}", response_model=list[TaskResponse])
async def get_agent_tasks(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> list[TaskResponse]:
    """
    Get tasks assigned to a specific agent.
    """
    service = TaskService(session)
    search_params = TaskSearchParams(
        assigned_agent_id=agent_id,
        limit=100
    )
    return await service.list_tasks(search_params)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Delete a task.

    Permanently removes the task from the system.
    """
    service = TaskService(session)
    success = await service.delete_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
