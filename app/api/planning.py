"""
Planning API Routes - Decision Making and Goal Decomposition

Provides endpoints for plan creation, execution, and management.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db_session
from app.models.planning import (
    Plan,
    PlanCreate,
    PlanUpdate,
    PlanResponse,
    Task,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    PlanExecutionRequest,
    PlanExecutionResult,
    PlanStatus,
    TaskStatus,
    PLAN_STATUSES,
    TASK_STATUSES,
)
from app.models.auth import TokenPayload
from app.services.planning_service import PlanningService

router = APIRouter(prefix="/api/planning", tags=["Planning"])


async def get_planning_service(
    session: AsyncSession = Depends(get_db_session),
) -> PlanningService:
    """Dependency to get PlanningService instance."""
    return PlanningService(session)


# Plan Management Endpoints


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: PlanCreate,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> PlanResponse:
    """
    Create a new plan with automatic goal decomposition.

    The system will decompose the goal into executable tasks.
    """
    return await service.create_plan(plan_data)


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> PlanResponse:
    """Get plan by ID with current progress."""
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )
    return plan


@router.get("/plans", response_model=list[PlanResponse])
async def list_agent_plans(
    agent_id: str,
    status: PlanStatus | None = None,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> list[PlanResponse]:
    """Get all plans for an agent, optionally filtered by status."""
    return await service.get_agent_plans(agent_id, status)


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: UUID,
    plan_update: PlanUpdate,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> PlanResponse:
    """Update plan status and progress."""
    if plan_update.status:
        plan = await service.update_plan_status(plan_id, plan_update.status, plan_update.progress)
    elif plan_update.progress is not None:
        plan = await service.update_plan_status(plan_id, None, plan_update.progress)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either status or progress must be provided"
        )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )
    return plan


@router.post("/plans/{plan_id}/execute", response_model=PlanExecutionResult)
async def execute_plan(
    plan_id: UUID,
    execution_request: PlanExecutionRequest,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> PlanExecutionResult:
    """
    Execute a plan with its tasks.

    Tasks will be executed with limited parallelism.
    """
    execution_request.plan_id = plan_id
    return await service.execute_plan(execution_request)


@router.post("/plans/{plan_id}/replan", response_model=PlanResponse)
async def replan_on_failure(
    plan_id: UUID,
    max_retries: int = 3,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> PlanResponse:
    """
    Create a new plan after failure, learning from mistakes.

    The system analyzes failed tasks and creates an adjusted plan.
    """
    plan = await service.replan_on_failure(plan_id, max_retries)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create replan for {plan_id} (max retries exceeded or not found)"
        )
    return plan


@router.get("/plans/{plan_id}/history", response_model=list[PlanResponse])
async def get_plan_history(
    plan_id: UUID,
    limit: int = 50,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> list[PlanResponse]:
    """Get plan history including retries and sub-plans."""
    # First get the original plan to find agent_id
    original_plan = await service.get_plan(plan_id)
    if not original_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )

    return await service.get_plan_history(original_plan.agent_id, from_plan=plan_id, limit=limit)


# Task Management Endpoints


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> TaskResponse:
    """Create a new task (usually handled automatically by plan creation)."""
    return await service.create_task(task_data)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> TaskResponse:
    """Get task by ID."""
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task


@router.get("/plans/{plan_id}/tasks", response_model=list[TaskResponse])
async def get_plan_tasks(
    plan_id: UUID,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> list[TaskResponse]:
    """Get all tasks for a plan."""
    return await service.get_plan_tasks(plan_id)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    current_user: TokenPayload = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> TaskResponse:
    """Update task status and result."""
    if not task_update.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be provided"
        )

    task = await service.update_task_status(
        task_id,
        task_update.status,
        task_update.result,
        task_update.error_message
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task


# Metadata Endpoints


@router.get("/meta/statuses")
async def get_plan_statuses() -> dict[str, list[str]]:
    """Get available plan and task statuses."""
    return {
        "plan_statuses": PLAN_STATUSES,
        "task_statuses": TASK_STATUSES,
    }


@router.get("/meta/info")
async def get_planning_info() -> dict[str, str]:
    """Get planning system information."""
    return {
        "system": "Planning Engine",
        "version": "1.0.0",
        "description": "Decision Making and Goal Decomposition for AI Agents",
        "features": [
            "Goal decomposition into tasks",
            "Parallel task execution",
            "Plan execution tracking",
            "Replanning on failure",
            "Plan history and analytics"
        ]
    }
