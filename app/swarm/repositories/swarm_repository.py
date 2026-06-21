"""
Swarm Repository - Data Access Layer for Swarm Operations
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.models.swarm import (
    Swarm,
    SwarmCreate,
    SwarmResponse,
    SwarmState,
    SwarmType,
)


class SwarmRepository:
    """
    Repository for Swarm operations.
    Manages swarm lifecycle and state.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_swarm(self, swarm_data: SwarmCreate) -> SwarmResponse:
        """
        Create a new swarm.

        Args:
            swarm_data: Swarm creation data

        Returns:
            Created swarm response
        """
        from app.swarm.models.swarm import SwarmDB

        swarm_db = SwarmDB(
            name=swarm_data.name,
            swarm_type=swarm_data.swarm_type.value if isinstance(swarm_data.swarm_type, SwarmType) else swarm_data.swarm_type,
            state="idle",
            config=swarm_data.config.model_dump(),
            agent_ids=[]
        )

        self.session.add(swarm_db)
        await self.session.flush()
        await self.session.refresh(swarm_db)

        return self._db_to_response(swarm_db)

    async def get_swarm(self, swarm_id: UUID) -> SwarmResponse | None:
        """
        Get swarm by ID.

        Args:
            swarm_id: Swarm UUID

        Returns:
            Swarm response or None if not found
        """
        from app.swarm.models.swarm import SwarmDB

        result = await self.session.execute(
            select(SwarmDB).where(SwarmDB.swarm_id == swarm_id)
        )
        swarm_db = result.scalar_one_or_none()

        if not swarm_db:
            return None

        return self._db_to_response(swarm_db)

    async def list_swarms(
        self,
        swarm_type: SwarmType | str | None = None,
        state: SwarmState | str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[SwarmResponse]:
        """
        List swarms with optional filtering.

        Args:
            swarm_type: Filter by swarm type
            state: Filter by state
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of swarms
        """
        from app.swarm.models.swarm import SwarmDB

        query = select(SwarmDB)

        # Apply filters
        conditions = []
        if swarm_type:
            swarm_type_value = swarm_type.value if isinstance(swarm_type, SwarmType) else swarm_type
            conditions.append(SwarmDB.swarm_type == swarm_type_value)
        if state:
            state_value = state.value if isinstance(state, SwarmState) else state
            conditions.append(SwarmDB.state == state_value)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by created_at descending (newest first)
        query = query.order_by(desc(SwarmDB.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        swarms = result.scalars().all()

        return [self._db_to_response(swarm) for swarm in swarms]

    async def update_swarm_state(
        self,
        swarm_id: UUID,
        state: SwarmState | str
    ) -> SwarmResponse | None:
        """
        Update swarm state.

        Args:
            swarm_id: Swarm UUID
            state: New state

        Returns:
            Updated swarm response or None if not found
        """
        from app.swarm.models.swarm import SwarmDB

        state_value = state.value if isinstance(state, SwarmState) else state

        result = await self.session.execute(
            select(SwarmDB).where(SwarmDB.swarm_id == swarm_id)
        )
        swarm_db = result.scalar_one_or_none()

        if not swarm_db:
            return None

        swarm_db.state = state_value
        swarm_db.updated_at = datetime.utcnow()

        if state_value == "running" and swarm_db.started_at is None:
            swarm_db.started_at = datetime.utcnow()
        elif state_value in ["completed", "terminated"] and swarm_db.stopped_at is None:
            swarm_db.stopped_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(swarm_db)

        return self._db_to_response(swarm_db)

    async def add_agent(self, swarm_id: UUID, agent_id: UUID) -> SwarmResponse | None:
        """
        Add an agent to a swarm.

        Args:
            swarm_id: Swarm UUID
            agent_id: Agent UUID

        Returns:
            Updated swarm response or None if not found
        """
        from app.swarm.models.swarm import SwarmDB

        result = await self.session.execute(
            select(SwarmDB).where(SwarmDB.swarm_id == swarm_id)
        )
        swarm_db = result.scalar_one_or_none()

        if not swarm_db:
            return None

        if agent_id not in swarm_db.agent_ids:
            swarm_db.agent_ids.append(agent_id)
            swarm_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(swarm_db)

        return self._db_to_response(swarm_db)

    async def remove_agent(self, swarm_id: UUID, agent_id: UUID) -> SwarmResponse | None:
        """
        Remove an agent from a swarm.

        Args:
            swarm_id: Swarm UUID
            agent_id: Agent UUID

        Returns:
            Updated swarm response or None if not found
        """
        from app.swarm.models.swarm import SwarmDB

        result = await self.session.execute(
            select(SwarmDB).where(SwarmDB.swarm_id == swarm_id)
        )
        swarm_db = result.scalar_one_or_none()

        if not swarm_db:
            return None

        if agent_id in swarm_db.agent_ids:
            swarm_db.agent_ids.remove(agent_id)
            swarm_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(swarm_db)

        return self._db_to_response(swarm_db)

    async def update_swarm_config(
        self,
        swarm_id: UUID,
        config: dict
    ) -> SwarmResponse | None:
        """
        Update swarm configuration.

        Args:
            swarm_id: Swarm UUID
            config: New configuration

        Returns:
            Updated swarm response or None if not found
        """
        from app.swarm.models.swarm import SwarmDB

        result = await self.session.execute(
            select(SwarmDB).where(SwarmDB.swarm_id == swarm_id)
        )
        swarm_db = result.scalar_one_or_none()

        if not swarm_db:
            return None

        swarm_db.config = config
        swarm_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(swarm_db)

        return self._db_to_response(swarm_db)

    async def delete_swarm(self, swarm_id: UUID) -> bool:
        """
        Delete a swarm.

        Args:
            swarm_id: Swarm UUID

        Returns:
            True if deleted, False if not found
        """
        from app.swarm.models.swarm import SwarmDB

        result = await self.session.execute(
            select(SwarmDB).where(SwarmDB.swarm_id == swarm_id)
        )
        swarm_db = result.scalar_one_or_none()

        if not swarm_db:
            return False

        await self.session.delete(swarm_db)
        await self.session.flush()

        return True

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
        from app.swarm.models.swarm import SwarmDB
        from sqlalchemy import func

        query = select(func.count(SwarmDB.swarm_id))

        conditions = []
        if swarm_type:
            swarm_type_value = swarm_type.value if isinstance(swarm_type, SwarmType) else swarm_type
            conditions.append(SwarmDB.swarm_type == swarm_type_value)
        if state:
            state_value = state.value if isinstance(state, SwarmState) else state
            conditions.append(SwarmDB.state == state_value)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_swarms_by_agent(self, agent_id: UUID) -> list[SwarmResponse]:
        """
        Get all swarms that contain a specific agent.

        Args:
            agent_id: Agent UUID

        Returns:
            List of swarms containing the agent
        """
        from app.swarm.models.swarm import SwarmDB

        # Using PostgreSQL array contains operator
        result = await self.session.execute(
            select(SwarmDB).where(SwarmDB.agent_ids.contains([str(agent_id)]))
        )
        swarms = result.scalars().all()

        return [self._db_to_response(swarm) for swarm in swarms]

    def _db_to_response(self, swarm_db) -> SwarmResponse:
        """Convert DB model to response model"""
        return SwarmResponse(
            swarm_id=swarm_db.swarm_id,
            name=swarm_db.name,
            swarm_type=swarm_db.swarm_type,
            state=swarm_db.state,
            config=swarm_db.config,
            agent_ids=swarm_db.agent_ids,
            created_at=swarm_db.created_at,
            updated_at=swarm_db.updated_at,
            started_at=swarm_db.started_at,
            stopped_at=swarm_db.stopped_at
        )
