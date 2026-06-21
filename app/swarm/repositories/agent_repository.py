"""
Agent Repository - Data Access Layer for Agent Operations
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.swarm.models.agent import (
    Agent,
    AgentCreate,
    AgentResponse,
    AgentState,
    AgentType,
)


class AgentRepository:
    """
    Repository for Agent operations.
    Manages agent lifecycle and state.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_agent(self, agent_data: AgentCreate) -> AgentResponse:
        """
        Create a new agent.

        Args:
            agent_data: Agent creation data

        Returns:
            Created agent response
        """
        from app.swarm.models.agent import AgentDB

        agent_db = AgentDB(
            agent_type=agent_data.agent_type.value if isinstance(agent_data.agent_type, AgentType) else agent_data.agent_type,
            name=agent_data.name,
            state="idle",
            capabilities=agent_data.capabilities,
            config=agent_data.config.model_dump(),
            last_heartbeat=datetime.utcnow()
        )

        self.session.add(agent_db)
        await self.session.flush()
        await self.session.refresh(agent_db)

        return AgentResponse(
            agent_id=agent_db.agent_id,
            agent_type=agent_db.agent_type,
            name=agent_db.name,
            state=agent_db.state,
            capabilities=agent_db.capabilities,
            config=agent_db.config,
            current_task_id=agent_db.current_task_id,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at,
            last_heartbeat=agent_db.last_heartbeat
        )

    async def get_agent(self, agent_id: UUID) -> AgentResponse | None:
        """
        Get agent by ID.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent response or None if not found
        """
        from app.swarm.models.agent import AgentDB

        result = await self.session.execute(
            select(AgentDB).where(AgentDB.agent_id == agent_id)
        )
        agent_db = result.scalar_one_or_none()

        if not agent_db:
            return None

        return AgentResponse(
            agent_id=agent_db.agent_id,
            agent_type=agent_db.agent_type,
            name=agent_db.name,
            state=agent_db.state,
            capabilities=agent_db.capabilities,
            config=agent_db.config,
            current_task_id=agent_db.current_task_id,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at,
            last_heartbeat=agent_db.last_heartbeat
        )

    async def list_agents(
        self,
        agent_type: AgentType | str | None = None,
        state: AgentState | str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[AgentResponse]:
        """
        List agents with optional filtering.

        Args:
            agent_type: Filter by agent type
            state: Filter by state
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of agents
        """
        from app.swarm.models.agent import AgentDB

        query = select(AgentDB)

        # Apply filters
        conditions = []
        if agent_type:
            agent_type_value = agent_type.value if isinstance(agent_type, AgentType) else agent_type
            conditions.append(AgentDB.agent_type == agent_type_value)
        if state:
            state_value = state.value if isinstance(state, AgentState) else state
            conditions.append(AgentDB.state == state_value)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by created_at descending (newest first)
        query = query.order_by(desc(AgentDB.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        agents = result.scalars().all()

        return [
            AgentResponse(
                agent_id=agent.agent_id,
                agent_type=agent.agent_type,
                name=agent.name,
                state=agent.state,
                capabilities=agent.capabilities,
                config=agent.config,
                current_task_id=agent.current_task_id,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                last_heartbeat=agent.last_heartbeat
            )
            for agent in agents
        ]

    async def update_agent_state(
        self,
        agent_id: UUID,
        state: AgentState | str
    ) -> AgentResponse | None:
        """
        Update agent state.

        Args:
            agent_id: Agent UUID
            state: New state

        Returns:
            Updated agent response or None if not found
        """
        from app.swarm.models.agent import AgentDB

        state_value = state.value if isinstance(state, AgentState) else state

        result = await self.session.execute(
            select(AgentDB).where(AgentDB.agent_id == agent_id)
        )
        agent_db = result.scalar_one_or_none()

        if not agent_db:
            return None

        agent_db.state = state_value
        agent_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(agent_db)

        return AgentResponse(
            agent_id=agent_db.agent_id,
            agent_type=agent_db.agent_type,
            name=agent_db.name,
            state=agent_db.state,
            capabilities=agent_db.capabilities,
            config=agent_db.config,
            current_task_id=agent_db.current_task_id,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at,
            last_heartbeat=agent_db.last_heartbeat
        )

    async def update_heartbeat(
        self,
        agent_id: UUID,
        current_task_id: UUID | None = None
    ) -> AgentResponse | None:
        """
        Update agent heartbeat.

        Args:
            agent_id: Agent UUID
            current_task_id: Current task ID (optional)

        Returns:
            Updated agent response or None if not found
        """
        from app.swarm.models.agent import AgentDB

        result = await self.session.execute(
            select(AgentDB).where(AgentDB.agent_id == agent_id)
        )
        agent_db = result.scalar_one_or_none()

        if not agent_db:
            return None

        agent_db.last_heartbeat = datetime.utcnow()
        if current_task_id is not None:
            agent_db.current_task_id = current_task_id

        await self.session.flush()
        await self.session.refresh(agent_db)

        return AgentResponse(
            agent_id=agent_db.agent_id,
            agent_type=agent_db.agent_type,
            name=agent_db.name,
            state=agent_db.state,
            capabilities=agent_db.capabilities,
            config=agent_db.config,
            current_task_id=agent_db.current_task_id,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at,
            last_heartbeat=agent_db.last_heartbeat
        )

    async def assign_task(self, agent_id: UUID, task_id: UUID) -> AgentResponse | None:
        """
        Assign a task to an agent.

        Args:
            agent_id: Agent UUID
            task_id: Task UUID

        Returns:
            Updated agent response or None if not found
        """
        from app.swarm.models.agent import AgentDB

        result = await self.session.execute(
            select(AgentDB).where(AgentDB.agent_id == agent_id)
        )
        agent_db = result.scalar_one_or_none()

        if not agent_db:
            return None

        agent_db.current_task_id = task_id
        agent_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(agent_db)

        return AgentResponse(
            agent_id=agent_db.agent_id,
            agent_type=agent_db.agent_type,
            name=agent_db.name,
            state=agent_db.state,
            capabilities=agent_db.capabilities,
            config=agent_db.config,
            current_task_id=agent_db.current_task_id,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at,
            last_heartbeat=agent_db.last_heartbeat
        )

    async def complete_task(self, agent_id: UUID) -> AgentResponse | None:
        """
        Clear current task from agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent response or None if not found
        """
        from app.swarm.models.agent import AgentDB

        result = await self.session.execute(
            select(AgentDB).where(AgentDB.agent_id == agent_id)
        )
        agent_db = result.scalar_one_or_none()

        if not agent_db:
            return None

        agent_db.current_task_id = None
        agent_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(agent_db)

        return AgentResponse(
            agent_id=agent_db.agent_id,
            agent_type=agent_db.agent_type,
            name=agent_db.name,
            state=agent_db.state,
            capabilities=agent_db.capabilities,
            config=agent_db.config,
            current_task_id=agent_db.current_task_id,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at,
            last_heartbeat=agent_db.last_heartbeat
        )

    async def delete_agent(self, agent_id: UUID) -> bool:
        """
        Delete an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            True if deleted, False if not found
        """
        from app.swarm.models.agent import AgentDB

        result = await self.session.execute(
            select(AgentDB).where(AgentDB.agent_id == agent_id)
        )
        agent_db = result.scalar_one_or_none()

        if not agent_db:
            return False

        await self.session.delete(agent_db)
        await self.session.flush()

        return True

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
        from app.swarm.models.agent import AgentDB
        from sqlalchemy import func

        query = select(func.count(AgentDB.agent_id))

        conditions = []
        if agent_type:
            agent_type_value = agent_type.value if isinstance(agent_type, AgentType) else agent_type
            conditions.append(AgentDB.agent_type == agent_type_value)
        if state:
            state_value = state.value if isinstance(state, AgentState) else state
            conditions.append(AgentDB.state == state_value)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_inactive_agents(self, timeout_seconds: int = 300) -> list[AgentResponse]:
        """
        Get agents that haven't sent a heartbeat within the timeout.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            List of inactive agents
        """
        from app.swarm.models.agent import AgentDB
        from datetime import timedelta

        timeout_threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        result = await self.session.execute(
            select(AgentDB)
            .where(AgentDB.last_heartbeat < timeout_threshold)
            .where(AgentDB.state == "active")
        )
        agents = result.scalars().all()

        return [
            AgentResponse(
                agent_id=agent.agent_id,
                agent_type=agent.agent_type,
                name=agent.name,
                state=agent.state,
                capabilities=agent.capabilities,
                config=agent.config,
                current_task_id=agent.current_task_id,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                last_heartbeat=agent.last_heartbeat
            )
            for agent in agents
        ]
