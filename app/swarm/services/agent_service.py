"""
Agent Service - Business Logic Layer for Agent Operations
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.models.agent import (
    Agent,
    AgentCreate,
    AgentHeartbeat,
    AgentMetrics,
    AgentResponse,
    AgentState,
    AgentType,
    AgentUpdate,
)
from app.swarm.repositories.agent_repository import AgentRepository


class AgentService:
    """
    Service layer for Agent operations.
    Handles agent lifecycle management and business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AgentRepository(session)

    async def create_agent(self, agent_data: AgentCreate) -> AgentResponse:
        """
        Create a new agent with validation.

        Args:
            agent_data: Agent creation data

        Returns:
            Created agent response

        Raises:
            ValueError: If agent data is invalid
        """
        # Validate agent name
        if not agent_data.name or not agent_data.name.strip():
            raise ValueError("Agent name is required")

        # Validate capabilities is a list
        if not isinstance(agent_data.capabilities, list):
            raise ValueError("Capabilities must be a list")

        # Create agent via repository
        return await self.repository.create_agent(agent_data)

    async def get_agent(self, agent_id: UUID) -> AgentResponse | None:
        """
        Get agent by ID.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent response or None
        """
        return await self.repository.get_agent(agent_id)

    async def list_agents(
        self,
        agent_type: AgentType | str | None = None,
        state: AgentState | str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[AgentResponse]:
        """
        List agents with filtering and pagination.

        Args:
            agent_type: Filter by agent type
            state: Filter by state
            limit: Max results
            offset: Pagination offset

        Returns:
            List of agents
        """
        # Validate limit
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.repository.list_agents(
            agent_type=agent_type,
            state=state,
            limit=limit,
            offset=offset
        )

    async def update_agent(
        self,
        agent_id: UUID,
        agent_data: AgentUpdate
    ) -> AgentResponse | None:
        """
        Update agent properties.

        Args:
            agent_id: Agent UUID
            agent_data: Update data

        Returns:
            Updated agent response or None
        """
        # Get current agent
        agent = await self.repository.get_agent(agent_id)
        if not agent:
            return None

        # Update state if provided
        if agent_data.state:
            await self.repository.update_agent_state(agent_id, agent_data.state)

        # Update capabilities if provided
        if agent_data.capabilities is not None:
            from sqlalchemy import update
            from app.swarm.models.agent import AgentDB

            await self.session.execute(
                update(AgentDB)
                .where(AgentDB.agent_id == agent_id)
                .values(capabilities=agent_data.capabilities, updated_at=datetime.utcnow())
            )
            await self.session.flush()

        # Update config if provided
        if agent_data.config:
            from sqlalchemy import update
            from app.swarm.models.agent import AgentDB

            await self.session.execute(
                update(AgentDB)
                .where(AgentDB.agent_id == agent_id)
                .values(config=agent_data.config.model_dump(), updated_at=datetime.utcnow())
            )
            await self.session.flush()

        return await self.repository.get_agent(agent_id)

    async def start_agent(self, agent_id: UUID) -> AgentResponse | None:
        """
        Start an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent response or None
        """
        return await self.repository.update_agent_state(agent_id, AgentState.ACTIVE)

    async def pause_agent(self, agent_id: UUID) -> AgentResponse | None:
        """
        Pause an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent response or None
        """
        return await self.repository.update_agent_state(agent_id, AgentState.PAUSED)

    async def resume_agent(self, agent_id: UUID) -> AgentResponse | None:
        """
        Resume a paused agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent response or None
        """
        return await self.repository.update_agent_state(agent_id, AgentState.ACTIVE)

    async def terminate_agent(self, agent_id: UUID) -> AgentResponse | None:
        """
        Terminate an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent response or None
        """
        # Clear current task if any
        agent = await self.repository.get_agent(agent_id)
        if agent and agent.current_task_id:
            await self.repository.complete_task(agent_id)

        return await self.repository.update_agent_state(agent_id, AgentState.TERMINATED)

    async def register_heartbeat(self, heartbeat: AgentHeartbeat) -> AgentResponse | None:
        """
        Register agent heartbeat.

        Args:
            heartbeat: Heartbeat data

        Returns:
            Updated agent response or None
        """
        # Update heartbeat and state
        await self.repository.update_heartbeat(
            heartbeat.agent_id,
            heartbeat.current_task_id
        )

        # Update state if different
        agent = await self.repository.get_agent(heartbeat.agent_id)
        if agent and agent.state != heartbeat.state.value:
            await self.repository.update_agent_state(heartbeat.agent_id, heartbeat.state)

        return await self.repository.get_agent(heartbeat.agent_id)

    async def assign_task(self, agent_id: UUID, task_id: UUID) -> AgentResponse | None:
        """
        Assign a task to an agent.

        Args:
            agent_id: Agent UUID
            task_id: Task UUID

        Returns:
            Updated agent response or None

        Raises:
            ValueError: If agent is not available
        """
        agent = await self.repository.get_agent(agent_id)
        if not agent:
            return None

        # Check if agent is available
        if agent.state not in [AgentState.IDLE.value, AgentState.ACTIVE.value]:
            raise ValueError(f"Agent {agent_id} is not available (state: {agent.state})")

        # Check if agent already has a task
        if agent.current_task_id:
            raise ValueError(f"Agent {agent_id} already has task {agent.current_task_id}")

        return await self.repository.assign_task(agent_id, task_id)

    async def complete_task(
        self,
        agent_id: UUID,
        result: dict | None = None
    ) -> AgentResponse | None:
        """
        Mark agent's current task as complete.

        Args:
            agent_id: Agent UUID
            result: Optional task result

        Returns:
            Updated agent response or None
        """
        return await self.repository.complete_task(agent_id)

    async def delete_agent(self, agent_id: UUID) -> bool:
        """
        Delete an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_agent(agent_id)

    async def get_agent_metrics(self, agent_id: UUID) -> AgentMetrics | None:
        """
        Get agent performance metrics.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent metrics or None
        """
        agent = await self.repository.get_agent(agent_id)
        if not agent:
            return None

        # Calculate metrics from task history would go here
        # For now, return default metrics
        return AgentMetrics(
            tasks_completed=0,
            tasks_failed=0,
            avg_task_duration=0.0,
            success_rate=0.0
        )

    async def check_inactive_agents(self, timeout_seconds: int = 300) -> list[AgentResponse]:
        """
        Check for inactive agents based on heartbeat timeout.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            List of inactive agents
        """
        return await self.repository.get_inactive_agents(timeout_seconds)

    async def count_agents(
        self,
        agent_type: AgentType | str | None = None,
        state: AgentState | str | None = None
    ) -> int:
        """
        Count agents matching filters.

        Args:
            agent_type: Filter by agent type
            state: Filter by state

        Returns:
            Number of matching agents
        """
        return await self.repository.count_agents(agent_type, state)
