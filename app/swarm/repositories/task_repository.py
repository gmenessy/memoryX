"""
Task Repository - Data Access Layer for Task Operations
"""
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.models.task import (
    Task,
    TaskCreate,
    TaskResponse,
    TaskState,
    TaskType,
)


class TaskRepository:
    """
    Repository for Task operations.
    Manages task distribution and tracking.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """
        Create a new task.

        Args:
            task_data: Task creation data

        Returns:
            Created task response
        """
        from app.swarm.models.task import TaskDB

        # Convert priority enum to integer
        if hasattr(task_data.priority, 'value'):
            priority_map = {
                "low": 1,
                "medium": 5,
                "high": 8,
                "critical": 10
            }
            priority_value = priority_map.get(task_data.priority.value, 5)
        else:
            priority_value = 5  # default

        task_db = TaskDB(
            swarm_id=task_data.swarm_id,
            task_type=task_data.task_type.value if isinstance(task_data.task_type, TaskType) else task_data.task_type,
            payload=task_data.payload,
            state="pending",
            priority=priority_value,
            timeout_at=datetime.utcnow() + timedelta(seconds=task_data.timeout_seconds)
        )

        self.session.add(task_db)
        await self.session.flush()
        await self.session.refresh(task_db)

        return self._db_to_response(task_db)

    async def get_task(self, task_id: UUID) -> TaskResponse | None:
        """
        Get task by ID.

        Args:
            task_id: Task UUID

        Returns:
            Task response or None if not found
        """
        from app.swarm.models.task import TaskDB

        result = await self.session.execute(
            select(TaskDB).where(TaskDB.task_id == task_id)
        )
        task_db = result.scalar_one_or_none()

        if not task_db:
            return None

        return self._db_to_response(task_db)

    async def list_tasks(
        self,
        swarm_id: UUID | None = None,
        assigned_agent_id: UUID | None = None,
        task_type: TaskType | str | None = None,
        state: TaskState | str | None = None,
        priority: int | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[TaskResponse]:
        """
        List tasks with optional filtering.

        Args:
            swarm_id: Filter by swarm ID
            assigned_agent_id: Filter by assigned agent
            task_type: Filter by task type
            state: Filter by state
            priority: Filter by minimum priority
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of tasks
        """
        from app.swarm.models.task import TaskDB

        query = select(TaskDB)

        # Apply filters
        conditions = []
        if swarm_id:
            conditions.append(TaskDB.swarm_id == swarm_id)
        if assigned_agent_id:
            conditions.append(TaskDB.assigned_agent_id == assigned_agent_id)
        if task_type:
            task_type_value = task_type.value if isinstance(task_type, TaskType) else task_type
            conditions.append(TaskDB.task_type == task_type_value)
        if state:
            state_value = state.value if isinstance(state, TaskState) else state
            conditions.append(TaskDB.state == state_value)
        if priority is not None:
            conditions.append(TaskDB.priority >= priority)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by priority descending, then created_at ascending
        query = query.order_by(desc(TaskDB.priority), TaskDB.created_at)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        tasks = result.scalars().all()

        return [self._db_to_response(task) for task in tasks]

    async def get_next_task(
        self,
        swarm_id: UUID,
        agent_id: UUID | None = None,
        limit: int = 10
    ) -> list[TaskResponse]:
        """
        Get next pending tasks for a swarm.

        Args:
            swarm_id: Swarm UUID
            agent_id: Optional agent ID to assign to
            limit: Maximum number of tasks to return

        Returns:
            List of pending tasks
        """
        from app.swarm.models.task import TaskDB

        # Get pending tasks ordered by priority
        result = await self.session.execute(
            select(TaskDB)
            .where(TaskDB.swarm_id == swarm_id)
            .where(TaskDB.state == "pending")
            .order_by(desc(TaskDB.priority), TaskDB.created_at)
            .limit(limit)
        )
        tasks = result.scalars().all()

        # If agent_id provided, assign tasks
        if agent_id and tasks:
            for task in tasks:
                await self.assign_task(task.task_id, agent_id)

        return [self._db_to_response(task) for task in tasks]

    async def assign_task(self, task_id: UUID, agent_id: UUID) -> TaskResponse | None:
        """
        Assign a task to an agent.

        Args:
            task_id: Task UUID
            agent_id: Agent UUID

        Returns:
            Updated task response or None if not found
        """
        from app.swarm.models.task import TaskDB

        result = await self.session.execute(
            select(TaskDB).where(TaskDB.task_id == task_id)
        )
        task_db = result.scalar_one_or_none()

        if not task_db:
            return None

        task_db.assigned_agent_id = agent_id
        task_db.state = "assigned"
        task_db.started_at = datetime.utcnow()
        task_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(task_db)

        return self._db_to_response(task_db)

    async def update_task_state(
        self,
        task_id: UUID,
        state: TaskState | str,
        result: dict | None = None,
        error: str | None = None
    ) -> TaskResponse | None:
        """
        Update task state.

        Args:
            task_id: Task UUID
            state: New state
            result: Optional result data
            error: Optional error message

        Returns:
            Updated task response or None if not found
        """
        from app.swarm.models.task import TaskDB

        state_value = state.value if isinstance(state, TaskState) else state

        result_db = await self.session.execute(
            select(TaskDB).where(TaskDB.task_id == task_id)
        )
        task_db = result_db.scalar_one_or_none()

        if not task_db:
            return None

        task_db.state = state_value
        task_db.updated_at = datetime.utcnow()

        if result is not None:
            task_db.result = result

        if error is not None:
            task_db.error = error

        # Handle completion
        if state_value in ["completed", "failed", "cancelled", "timeout"]:
            task_db.completed_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(task_db)

        return self._db_to_response(task_db)

    async def complete_task(self, task_id: UUID, result: dict) -> TaskResponse | None:
        """
        Mark a task as completed.

        Args:
            task_id: Task UUID
            result: Task result

        Returns:
            Updated task response or None if not found
        """
        return await self.update_task_state(task_id, TaskState.COMPLETED, result=result)

    async def fail_task(self, task_id: UUID, error: str) -> TaskResponse | None:
        """
        Mark a task as failed.

        Args:
            task_id: Task UUID
            error: Error message

        Returns:
            Updated task response or None if not found
        """
        from app.swarm.models.task import TaskDB

        result_db = await self.session.execute(
            select(TaskDB).where(TaskDB.task_id == task_id)
        )
        task_db = result_db.scalar_one_or_none()

        if not task_db:
            return None

        # Increment retry count
        task_db.retry_count += 1

        # Check if we should retry
        if task_db.retry_count < task_db.max_retries:
            task_db.state = "pending"
            task_db.assigned_agent_id = None
            task_db.started_at = None
            task_db.error = error
        else:
            # Max retries reached, mark as failed
            task_db.state = "failed"
            task_db.error = error
            task_db.completed_at = datetime.utcnow()

        task_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(task_db)

        return self._db_to_response(task_db)

    async def cancel_task(self, task_id: UUID) -> TaskResponse | None:
        """
        Cancel a task.

        Args:
            task_id: Task UUID

        Returns:
            Updated task response or None if not found
        """
        return await self.update_task_state(task_id, TaskState.CANCELLED)

    async def get_timed_out_tasks(self) -> list[TaskResponse]:
        """
        Get tasks that have timed out.

        Returns:
            List of timed out tasks
        """
        from app.swarm.models.task import TaskDB

        now = datetime.utcnow()

        result = await self.session.execute(
            select(TaskDB)
            .where(TaskDB.timeout_at < now)
            .where(TaskDB.state.in_(["pending", "assigned", "in_progress"]))
        )
        tasks = result.scalars().all()

        # Mark as timed out
        for task in tasks:
            task.state = "timeout"
            task.completed_at = now
            task.updated_at = now

        await self.session.flush()

        return [self._db_to_response(task) for task in tasks]

    async def count_tasks(
        self,
        swarm_id: UUID | None = None,
        state: TaskState | str | None = None
    ) -> int:
        """
        Count tasks matching filters.

        Args:
            swarm_id: Filter by swarm ID
            state: Filter by state

        Returns:
            Number of matching tasks
        """
        from app.swarm.models.task import TaskDB
        from sqlalchemy import func

        query = select(func.count(TaskDB.task_id))

        conditions = []
        if swarm_id:
            conditions.append(TaskDB.swarm_id == swarm_id)
        if state:
            state_value = state.value if isinstance(state, TaskState) else state
            conditions.append(TaskDB.state == state_value)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_task_statistics(self, swarm_id: UUID) -> dict:
        """
        Get task statistics for a swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Dictionary with task statistics
        """
        from sqlalchemy import func, case
        from app.swarm.models.task import TaskDB

        result = await self.session.execute(
            select(
                func.count(TaskDB.task_id).label('total'),
                func.sum(case((TaskDB.state == 'completed', 1), else_=0)).label('completed'),
                func.sum(case((TaskDB.state == 'failed', 1), else_=0)).label('failed'),
                func.sum(case((TaskDB.state == 'pending', 1), else_=0)).label('pending'),
                func.sum(case((TaskDB.state == 'in_progress', 1), else_=0)).label('in_progress')
            )
            .where(TaskDB.swarm_id == swarm_id)
        )
        stats = result.one()

        return {
            "total": stats.total or 0,
            "completed": stats.completed or 0,
            "failed": stats.failed or 0,
            "pending": stats.pending or 0,
            "in_progress": stats.in_progress or 0
        }

    async def delete_task(self, task_id: UUID) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task UUID

        Returns:
            True if deleted, False if not found
        """
        from app.swarm.models.task import TaskDB

        result = await self.session.execute(
            select(TaskDB).where(TaskDB.task_id == task_id)
        )
        task_db = result.scalar_one_or_none()

        if not task_db:
            return False

        await self.session.delete(task_db)
        await self.session.flush()

        return True

    def _db_to_response(self, task_db) -> TaskResponse:
        """Convert DB model to response model"""
        return TaskResponse(
            task_id=task_db.task_id,
            swarm_id=task_db.swarm_id,
            assigned_agent_id=task_db.assigned_agent_id,
            task_type=task_db.task_type,
            payload=task_db.payload,
            state=task_db.state,
            priority=task_db.priority,
            result=task_db.result,
            error=task_db.error,
            retry_count=task_db.retry_count,
            max_retries=task_db.max_retries,
            created_at=task_db.created_at,
            updated_at=task_db.updated_at,
            started_at=task_db.started_at,
            completed_at=task_db.completed_at,
            timeout_at=task_db.timeout_at
        )
