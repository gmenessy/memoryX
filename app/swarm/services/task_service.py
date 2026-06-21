"""
Task Service - Business Logic Layer for Task Operations
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.models.task import (
    Task,
    TaskAssignment,
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskResult,
    TaskSearchParams,
    TaskState,
    TaskType,
)
from app.swarm.repositories.task_repository import TaskRepository


class TaskService:
    """
    Service layer for Task operations.
    Handles task distribution and coordination.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = TaskRepository(session)

    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """
        Create a new task with validation.

        Args:
            task_data: Task creation data

        Returns:
            Created task response

        Raises:
            ValueError: If task data is invalid
        """
        # Validate swarm exists
        from app.swarm.repositories.swarm_repository import SwarmRepository
        swarm_repo = SwarmRepository(self.session)
        swarm = await swarm_repo.get_swarm(task_data.swarm_id)
        if not swarm:
            raise ValueError(f"Swarm {task_data.swarm_id} not found")

        # Validate timeout
        if task_data.timeout_seconds < 10:
            raise ValueError("Timeout must be at least 10 seconds")

        # Create task via repository
        return await self.repository.create_task(task_data)

    async def get_task(self, task_id: UUID) -> TaskResponse | None:
        """
        Get task by ID.

        Args:
            task_id: Task UUID

        Returns:
            Task response or None
        """
        return await self.repository.get_task(task_id)

    async def list_tasks(
        self,
        search_params: TaskSearchParams
    ) -> list[TaskResponse]:
        """
        List tasks with filtering and pagination.

        Args:
            search_params: Search parameters

        Returns:
            List of tasks
        """
        # Validate limit
        if search_params.limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if search_params.limit < 1:
            raise ValueError("Limit must be at least 1")

        if search_params.offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.repository.list_tasks(
            swarm_id=search_params.swarm_id,
            assigned_agent_id=search_params.assigned_agent_id,
            task_type=search_params.task_type,
            state=search_params.state,
            priority=None,  # Would need conversion from enum
            limit=search_params.limit,
            offset=search_params.offset
        )

    async def assign_task(
        self,
        task_id: UUID,
        agent_id: UUID
    ) -> TaskResponse | None:
        """
        Assign a task to an agent.

        Args:
            task_id: Task UUID
            agent_id: Agent UUID

        Returns:
            Updated task response or None

        Raises:
            ValueError: If assignment fails
        """
        # Validate task exists and is assignable
        task = await self.repository.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.state not in ["pending", "failed"]:
            raise ValueError(f"Task {task_id} is not assignable (state: {task.state})")

        # Validate agent exists
        from app.swarm.repositories.agent_repository import AgentRepository
        agent_repo = AgentRepository(self.session)
        agent = await agent_repo.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        if agent.state not in ["idle", "active"]:
            raise ValueError(f"Agent {agent_id} is not available (state: {agent.state})")

        # Assign task
        result = await self.repository.assign_task(task_id, agent_id)
        if result:
            # Also update agent
            await agent_repo.assign_task(agent_id, task_id)

        return result

    async def complete_task(
        self,
        task_id: UUID,
        agent_id: UUID,
        result: dict
    ) -> TaskResponse | None:
        """
        Complete a task with result.

        Args:
            task_id: Task UUID
            agent_id: Agent UUID
            result: Task result

        Returns:
            Updated task response or None
        """
        # Validate task is assigned to this agent
        task = await self.repository.get_task(task_id)
        if not task:
            return None

        if task.assigned_agent_id != agent_id:
            raise ValueError(f"Task {task_id} is not assigned to agent {agent_id}")

        # Complete task
        result_response = await self.repository.complete_task(task_id, result)

        if result_response:
            # Clear agent's current task
            from app.swarm.repositories.agent_repository import AgentRepository
            agent_repo = AgentRepository(self.session)
            await agent_repo.complete_task(agent_id)

        return result_response

    async def fail_task(
        self,
        task_id: UUID,
        agent_id: UUID,
        error: str
    ) -> TaskResponse | None:
        """
        Mark a task as failed.

        Args:
            task_id: Task UUID
            agent_id: Agent UUID
            error: Error message

        Returns:
            Updated task response or None
        """
        # Validate task is assigned to this agent
        task = await self.repository.get_task(task_id)
        if not task:
            return None

        if task.assigned_agent_id != agent_id:
            raise ValueError(f"Task {task_id} is not assigned to agent {agent_id}")

        # Fail task (will retry if retries available)
        result = await self.repository.fail_task(task_id, error)

        if result and result.state != "pending":  # Not retrying
            # Clear agent's current task
            from app.swarm.repositories.agent_repository import AgentRepository
            agent_repo = AgentRepository(self.session)
            await agent_repo.complete_task(agent_id)

        return result

    async def cancel_task(self, task_id: UUID) -> TaskResponse | None:
        """
        Cancel a task.

        Args:
            task_id: Task UUID

        Returns:
            Updated task response or None
        """
        task = await self.repository.get_task(task_id)
        if not task:
            return None

        result = await self.repository.cancel_task(task_id)

        # Clear agent's current task if assigned
        if task.assigned_agent_id:
            from app.swarm.repositories.agent_repository import AgentRepository
            agent_repo = AgentRepository(self.session)
            await agent_repo.complete_task(task.assigned_agent_id)

        return result

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
            limit: Maximum tasks to return

        Returns:
            List of pending tasks
        """
        return await self.repository.get_next_task(swarm_id, agent_id, limit)

    async def get_task_statistics(self, swarm_id: UUID) -> dict:
        """
        Get task statistics for a swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Task statistics dictionary
        """
        return await self.repository.get_task_statistics(swarm_id)

    async def process_timed_out_tasks(self) -> list[TaskResponse]:
        """
        Process timed out tasks.

        Returns:
            List of timed out tasks
        """
        return await self.repository.get_timed_out_tasks()

    async def delete_task(self, task_id: UUID) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task UUID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_task(task_id)

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
        return await self.repository.count_tasks(swarm_id, state)
