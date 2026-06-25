"""
Planning Repository - Data Access Layer for Plans
"""
from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import (
    PlanDB,
    TaskDB,
    PlanCreate,
    TaskCreate,
    PlanResponse,
    TaskResponse,
    PlanStatus,
    TaskStatus,
)


class PlanRepository:
    """Repository for Plan operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(self, plan_data: PlanCreate) -> PlanResponse:
        """Create a new plan."""
        plan_db = PlanDB(
            agent_id=plan_data.agent_id,
            goal=plan_data.goal,
            plan_data=plan_data.plan_data,
            parent_plan_id=plan_data.parent_plan_id
        )

        self.session.add(plan_db)
        await self.session.flush()
        await self.session.refresh(plan_db)

        return PlanResponse(
            plan_id=plan_db.plan_id,
            agent_id=plan_db.agent_id,
            goal=plan_db.goal,
            plan_data=plan_db.plan_data,
            status=PlanStatus(plan_db.status),
            progress=plan_db.progress,
            parent_plan_id=plan_db.parent_plan_id,
            created_at=plan_db.created_at,
            updated_at=plan_db.updated_at,
            completed_at=plan_db.completed_at
        )

    async def get_plan(self, plan_id: UUID) -> PlanResponse | None:
        """Get plan by ID."""
        result = await self.session.execute(
            select(PlanDB).where(PlanDB.plan_id == plan_id)
        )
        plan_db = result.scalar_one_or_none()

        if not plan_db:
            return None

        # Get task counts
        task_counts = await self._get_plan_task_counts(plan_id)

        return PlanResponse(
            plan_id=plan_db.plan_id,
            agent_id=plan_db.agent_id,
            goal=plan_db.goal,
            plan_data=plan_db.plan_data,
            status=PlanStatus(plan_db.status),
            progress=plan_db.progress,
            parent_plan_id=plan_db.parent_plan_id,
            created_at=plan_db.created_at,
            updated_at=plan_db.updated_at,
            completed_at=plan_db.completed_at,
            task_count=task_counts["total"],
            completed_tasks=task_counts["completed"],
            failed_tasks=task_counts["failed"]
        )

    async def update_plan_status(
        self,
        plan_id: UUID,
        status: PlanStatus,
        progress: float | None = None
    ) -> PlanResponse | None:
        """Update plan status."""
        plan_db = await self._get_plan_db(plan_id)
        if not plan_db:
            return None

        plan_db.status = status.value
        if progress is not None:
            plan_db.progress = progress

        if status == PlanStatus.COMPLETED:
            plan_db.completed_at = datetime.utcnow()
            plan_db.progress = 1.0

        await self.session.flush()
        await self.session.refresh(plan_db)

        return await self.get_plan(plan_id)

    async def get_agent_plans(
        self,
        agent_id: str,
        status: PlanStatus | None = None,
        limit: int = 100
    ) -> list[PlanResponse]:
        """Get plans for an agent."""
        query = select(PlanDB).where(PlanDB.agent_id == agent_id)

        if status:
            query = query.where(PlanDB.status == status.value)

        query = query.order_by(PlanDB.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        plans = result.scalars().all()

        responses = []
        for plan_db in plans:
            task_counts = await self._get_plan_task_counts(plan_db.plan_id)
            responses.append(
                PlanResponse(
                    plan_id=plan_db.plan_id,
                    agent_id=plan_db.agent_id,
                    goal=plan_db.goal,
                    plan_data=plan_db.plan_data,
                    status=PlanStatus(plan_db.status),
                    progress=plan_db.progress,
                    parent_plan_id=plan_db.parent_plan_id,
                    created_at=plan_db.created_at,
                    updated_at=plan_db.updated_at,
                    completed_at=plan_db.completed_at,
                    task_count=task_counts["total"],
                    completed_tasks=task_counts["completed"],
                    failed_tasks=task_counts["failed"]
                )
            )

        return responses

    async def _get_plan_db(self, plan_id: UUID) -> PlanDB | None:
        """Get plan DB model."""
        result = await self.session.execute(
            select(PlanDB).where(PlanDB.plan_id == plan_id)
        )
        return result.scalar_one_or_none()

    async def _get_plan_task_counts(self, plan_id: UUID) -> dict[str, int]:
        """Get task counts for a plan."""
        total_result = await self.session.execute(
            select(func.count(TaskDB.task_id)).where(TaskDB.plan_id == plan_id)
        )
        total = total_result.scalar() or 0

        completed_result = await self.session.execute(
            select(func.count(TaskDB.task_id)).where(
                and_(TaskDB.plan_id == plan_id, TaskDB.status == TaskStatus.COMPLETED.value)
            )
        )
        completed = completed_result.scalar() or 0

        failed_result = await self.session.execute(
            select(func.count(TaskDB.task_id)).where(
                and_(TaskDB.plan_id == plan_id, TaskDB.status == TaskStatus.FAILED.value)
            )
        )
        failed = failed_result.scalar() or 0

        return {
            "total": total,
            "completed": completed,
            "failed": failed
        }


class TaskRepository:
    """Repository for Task operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """Create a new task."""
        task_db = TaskDB(
            plan_id=task_data.plan_id,
            parent_task_id=task_data.parent_task_id,
            title=task_data.title,
            description=task_data.description,
            task_type=task_data.task_type,
            parameters=task_data.parameters,
            priority=task_data.priority.value,
            estimated_duration=task_data.estimated_duration
        )

        self.session.add(task_db)
        await self.session.flush()
        await self.session.refresh(task_db)

        return TaskResponse(
            task_id=task_db.task_id,
            plan_id=task_db.plan_id,
            parent_task_id=task_db.parent_task_id,
            title=task_db.title,
            description=task_db.description,
            task_type=task_db.task_type,
            parameters=task_db.parameters,
            status=TaskStatus(task_db.status),
            priority=TaskPriority(task_db.priority),
            estimated_duration=task_db.estimated_duration,
            actual_duration=task_db.actual_duration,
            result=task_db.result,
            error_message=task_db.error_message,
            created_at=task_db.created_at,
            started_at=task_db.started_at,
            completed_at=task_db.completed_at
        )

    async def get_task(self, task_id: UUID) -> TaskResponse | None:
        """Get task by ID."""
        result = await self.session.execute(
            select(TaskDB).where(TaskDB.task_id == task_id)
        )
        task_db = result.scalar_one_or_none()

        if not task_db:
            return None

        return TaskResponse(
            task_id=task_db.task_id,
            plan_id=task_db.plan_id,
            parent_task_id=task_db.parent_task_id,
            title=task_db.title,
            description=task_db.description,
            task_type=task_db.task_type,
            parameters=task_db.parameters,
            status=TaskStatus(task_db.status),
            priority=TaskPriority(task_db.priority),
            estimated_duration=task_db.estimated_duration,
            actual_duration=task_db.actual_duration,
            result=task_db.result,
            error_message=task_db.error_message,
            created_at=task_db.created_at,
            started_at=task_db.started_at,
            completed_at=task_db.completed_at
        )

    async def update_task(
        self,
        task_id: UUID,
        status: TaskStatus | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None
    ) -> TaskResponse | None:
        """Update task status and result."""
        task_db = await self._get_task_db(task_id)
        if not task_db:
            return None

        if status:
            task_db.status = status.value
            if status == TaskStatus.IN_PROGRESS and not task_db.started_at:
                task_db.started_at = datetime.utcnow()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]:
                task_db.completed_at = datetime.utcnow()
                if task_db.started_at:
                    duration = (task_db.completed_at - task_db.started_at).total_seconds()
                    task_db.actual_duration = duration

        if result is not None:
            task_db.result = result

        if error_message:
            task_db.error_message = error_message

        await self.session.flush()
        await self.session.refresh(task_db)

        return await self.get_task(task_id)

    async def get_plan_tasks(
        self,
        plan_id: UUID,
        status: TaskStatus | None = None
    ) -> list[TaskResponse]:
        """Get all tasks for a plan."""
        query = select(TaskDB).where(TaskDB.plan_id == plan_id)

        if status:
            query = query.where(TaskDB.status == status.value)

        query = query.order_by(TaskDB.created_at.asc())

        result = await self.session.execute(query)
        tasks = result.scalars().all()

        return [
            TaskResponse(
                task_id=task.task_id,
                plan_id=task.plan_id,
                parent_task_id=task.parent_task_id,
                title=task.title,
                description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                status=TaskStatus(task.status),
                priority=TaskPriority(task.priority),
                estimated_duration=task.estimated_duration,
                actual_duration=task.actual_duration,
                result=task.result,
                error_message=task.error_message,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            for task in tasks
        ]

    async def get_pending_tasks(
        self,
        plan_id: UUID,
        limit: int = 10
    ) -> list[TaskResponse]:
        """Get pending tasks ordered by priority."""
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }

        # Get pending tasks
        result = await self.session.execute(
            select(TaskDB)
            .where(
                and_(
                    TaskDB.plan_id == plan_id,
                    TaskDB.status == TaskStatus.PENDING.value
                )
            )
            .order_by(TaskDB.created_at.asc())
            .limit(limit * 2)  # Get more than needed for sorting
        )
        tasks = result.scalars().all()

        # Sort by priority
        sorted_tasks = sorted(
            tasks,
            key=lambda t: priority_order.get(t.priority, 999)
        )[:limit]

        return [
            TaskResponse(
                task_id=task.task_id,
                plan_id=task.plan_id,
                parent_task_id=task.parent_task_id,
                title=task.title,
                description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                status=TaskStatus(task.status),
                priority=TaskPriority(task.priority),
                estimated_duration=task.estimated_duration,
                actual_duration=task.actual_duration,
                result=task.result,
                error_message=task.error_message,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            for task in sorted_tasks
        ]

    async def _get_task_db(self, task_id: UUID) -> TaskDB | None:
        """Get task DB model."""
        result = await self.session.execute(
            select(TaskDB).where(TaskDB.task_id == task_id)
        )
        return result.scalar_one_or_none()
