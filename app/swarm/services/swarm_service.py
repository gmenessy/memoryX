"""
Swarm Service - Business Logic Layer for Swarm Operations
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.models.swarm import (
    Swarm,
    SwarmConfig,
    SwarmCreate,
    SwarmMetrics,
    SwarmResponse,
    SwarmState,
    SwarmStatus,
    SwarmType,
    SwarmUpdate,
)
from app.swarm.repositories.swarm_repository import SwarmRepository
from app.swarm.repositories.agent_repository import AgentRepository
from app.swarm.repositories.task_repository import TaskRepository


class SwarmService:
    """
    Service layer for Swarm operations.
    Handles swarm orchestration and coordination.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SwarmRepository(session)
        self.agent_repository = AgentRepository(session)
        self.task_repository = TaskRepository(session)

    async def create_swarm(self, swarm_data: SwarmCreate) -> SwarmResponse:
        """
        Create a new swarm with validation.

        Args:
            swarm_data: Swarm creation data

        Returns:
            Created swarm response

        Raises:
            ValueError: If swarm data is invalid
        """
        # Validate swarm name
        if not swarm_data.name or not swarm_data.name.strip():
            raise ValueError("Swarm name is required")

        # Create swarm via repository
        swarm = await self.repository.create_swarm(swarm_data)

        # Create initial agents if requested
        if swarm_data.initial_agent_count > 0:
            from app.swarm.models.agent import AgentCreate, AgentType

            agent_type_map = {
                SwarmType.EVAL: AgentType.EVAL,
                SwarmType.RESEARCH: AgentType.RESEARCH,
                SwarmType.SIMULATION: AgentType.SIMULATION,
                SwarmType.LEARNING: AgentType.LEARNING,
                SwarmType.MUTATION: AgentType.MUTATION,
                SwarmType.OPTIMIZATION: AgentType.OPTIMIZATION,
                SwarmType.RECURSIVE: AgentType.RECURSIVE,
                SwarmType.GOVERNANCE: AgentType.BASE,
            }

            agent_type = agent_type_map.get(swarm_data.swarm_type, AgentType.BASE)

            for i in range(swarm_data.initial_agent_count):
                agent_data = AgentCreate(
                    agent_type=agent_type,
                    name=f"{swarm_data.name}_agent_{i+1}",
                    capabilities=["task_execution"]
                )
                agent = await self.agent_repository.create_agent(agent_data)
                await self.repository.add_agent(swarm.swarm_id, agent.agent_id)

        return await self.repository.get_swarm(swarm.swarm_id)

    async def get_swarm(self, swarm_id: UUID) -> SwarmResponse | None:
        """
        Get swarm by ID.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Swarm response or None
        """
        return await self.repository.get_swarm(swarm_id)

    async def list_swarms(
        self,
        swarm_type: SwarmType | str | None = None,
        state: SwarmState | str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[SwarmResponse]:
        """
        List swarms with filtering and pagination.

        Args:
            swarm_type: Filter by swarm type
            state: Filter by state
            limit: Max results
            offset: Pagination offset

        Returns:
            List of swarms
        """
        # Validate limit
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.repository.list_swarms(
            swarm_type=swarm_type,
            state=state,
            limit=limit,
            offset=offset
        )

    async def start_swarm(self, swarm_id: UUID) -> SwarmResponse | None:
        """
        Start a swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Updated swarm response or None
        """
        swarm = await self.repository.get_swarm(swarm_id)
        if not swarm:
            return None

        # Update all agents to active
        for agent_id in swarm.agent_ids:
            await self.agent_repository.update_agent_state(agent_id, "active")

        return await self.repository.update_swarm_state(swarm_id, SwarmState.RUNNING)

    async def pause_swarm(self, swarm_id: UUID) -> SwarmResponse | None:
        """
        Pause a swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Updated swarm response or None
        """
        swarm = await self.repository.get_swarm(swarm_id)
        if not swarm:
            return None

        # Pause all agents
        for agent_id in swarm.agent_ids:
            await self.agent_repository.update_agent_state(agent_id, "paused")

        return await self.repository.update_swarm_state(swarm_id, SwarmState.PAUSED)

    async def resume_swarm(self, swarm_id: UUID) -> SwarmResponse | None:
        """
        Resume a paused swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Updated swarm response or None
        """
        return await self.start_swarm(swarm_id)

    async def terminate_swarm(self, swarm_id: UUID) -> SwarmResponse | None:
        """
        Terminate a swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Updated swarm response or None
        """
        swarm = await self.repository.get_swarm(swarm_id)
        if not swarm:
            return None

        # Terminate all agents
        for agent_id in swarm.agent_ids:
            await self.agent_repository.update_agent_state(agent_id, "terminated")

        return await self.repository.update_swarm_state(swarm_id, SwarmState.TERMINATED)

    async def add_agent(self, swarm_id: UUID, agent_id: UUID) -> SwarmResponse | None:
        """
        Add an agent to a swarm.

        Args:
            swarm_id: Swarm UUID
            agent_id: Agent UUID

        Returns:
            Updated swarm response or None

        Raises:
            ValueError: If agent is already in a swarm
        """
        # Check if agent exists
        agent = await self.agent_repository.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Check if agent is already in this swarm
        swarm = await self.repository.get_swarm(swarm_id)
        if swarm and agent_id in swarm.agent_ids:
            raise ValueError(f"Agent {agent_id} is already in swarm {swarm_id}")

        return await self.repository.add_agent(swarm_id, agent_id)

    async def remove_agent(self, swarm_id: UUID, agent_id: UUID) -> SwarmResponse | None:
        """
        Remove an agent from a swarm.

        Args:
            swarm_id: Swarm UUID
            agent_id: Agent UUID

        Returns:
            Updated swarm response or None
        """
        swarm = await self.repository.get_swarm(swarm_id)
        if not swarm:
            return None

        # Pause agent if active
        agent = await self.agent_repository.get_agent(agent_id)
        if agent and agent.state == "active":
            await self.agent_repository.update_agent_state(agent_id, "idle")

        return await self.repository.remove_agent(swarm_id, agent_id)

    async def update_swarm(
        self,
        swarm_id: UUID,
        swarm_data: SwarmUpdate
    ) -> SwarmResponse | None:
        """
        Update swarm properties.

        Args:
            swarm_id: Swarm UUID
            swarm_data: Update data

        Returns:
            Updated swarm response or None
        """
        # Update state if provided
        if swarm_data.state:
            await self.repository.update_swarm_state(swarm_id, swarm_data.state)

        # Update config if provided
        if swarm_data.config:
            await self.repository.update_swarm_config(swarm_id, swarm_data.config.model_dump())

        return await self.repository.get_swarm(swarm_id)

    async def get_swarm_status(self, swarm_id: UUID) -> SwarmStatus | None:
        """
        Get detailed swarm status.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Detailed swarm status or None
        """
        swarm = await self.repository.get_swarm(swarm_id)
        if not swarm:
            return None

        # Get agent states
        active_agents = 0
        idle_agents = 0
        error_agents = 0

        for agent_id in swarm.agent_ids:
            agent = await self.agent_repository.get_agent(agent_id)
            if agent:
                if agent.state == "active":
                    active_agents += 1
                elif agent.state == "idle":
                    idle_agents += 1
                elif agent.state == "error":
                    error_agents += 1

        # Get task statistics
        task_stats = await self.task_repository.get_task_statistics(swarm_id)

        # Calculate uptime
        uptime = None
        if swarm.started_at:
            if swarm.stopped_at:
                uptime = (swarm.stopped_at - swarm.started_at).seconds
            else:
                uptime = (datetime.utcnow() - swarm.started_at).seconds

        return SwarmStatus(
            swarm_id=swarm.swarm_id,
            name=swarm.name,
            swarm_type=swarm.swarm_type,
            state=swarm.state,
            agent_count=len(swarm.agent_ids),
            active_agents=active_agents,
            idle_agents=idle_agents,
            error_agents=error_agents,
            tasks_pending=task_stats["pending"],
            tasks_in_progress=task_stats["in_progress"],
            tasks_completed=task_stats["completed"],
            tasks_failed=task_stats["failed"],
            uptime_seconds=uptime
        )

    async def get_swarm_metrics(self, swarm_id: UUID) -> SwarmMetrics | None:
        """
        Get swarm performance metrics.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Swarm metrics or None
        """
        swarm = await self.repository.get_swarm(swarm_id)
        if not swarm:
            return None

        # Get task statistics
        task_stats = await self.task_repository.get_task_statistics(swarm_id)

        # Calculate metrics
        total_tasks = task_stats["total"]
        completed_tasks = task_stats["completed"]
        failed_tasks = task_stats["failed"]

        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        agent_utilization = len(swarm.agent_ids) / max(1, len(swarm.agent_ids))

        # Simple throughput calculation (tasks per minute would need timing data)
        throughput = completed_tasks / 1.0  # Placeholder

        return SwarmMetrics(
            swarm_id=swarm.swarm_id,
            timestamp=datetime.utcnow(),
            total_tasks_processed=total_tasks,
            avg_task_duration=0.0,  # Would need timing data
            success_rate=success_rate,
            agent_utilization=agent_utilization,
            throughput_per_minute=throughput
        )

    async def delete_swarm(self, swarm_id: UUID) -> bool:
        """
        Delete a swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            True if deleted, False if not found
        """
        swarm = await self.repository.get_swarm(swarm_id)
        if not swarm:
            return False

        # Terminate all agents first
        for agent_id in swarm.agent_ids:
            await self.agent_repository.delete_agent(agent_id)

        return await self.repository.delete_swarm(swarm_id)

    async def count_swarms(
        self,
        swarm_type: SwarmType | str | None = None,
        state: SwarmState | str | None = None
    ) -> int:
        """
        Count swarms matching filters.

        Args:
            swarm_type: Filter by swarm type
            state: Filter by state

        Returns:
            Number of matching swarms
        """
        return await self.repository.count_swarms(swarm_type, state)
