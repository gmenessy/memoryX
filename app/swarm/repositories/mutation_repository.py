"""
Mutation Repository - Data Access Layer for Mutation Operations
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.models.mutation import (
    Mutation,
    MutationCreate,
    MutationResponse,
    MutationState,
    MutationType,
)


class MutationRepository:
    """
    Repository for Mutation operations.
    Manages prompt mutations and A/B testing.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_mutation(
        self,
        source_prompt_id: UUID,
        target_prompt_id: UUID,
        mutation_data: MutationCreate
    ) -> MutationResponse:
        """
        Create a new mutation.

        Args:
            source_prompt_id: Source prompt UUID
            target_prompt_id: Target (new) prompt UUID
            mutation_data: Mutation creation data

        Returns:
            Created mutation response
        """
        from app.swarm.models.mutation import MutationDB
        from app.swarm.repositories.prompt_repository import PromptRepository

        mutation_db = MutationDB(
            source_prompt_id=source_prompt_id,
            target_prompt_id=target_prompt_id,
            mutation_type=mutation_data.mutation_type.value if isinstance(mutation_data.mutation_type, MutationType) else mutation_data.mutation_type,
            description=mutation_data.description,
            confidence=mutation_data.confidence,
            state="draft"
        )

        self.session.add(mutation_db)
        await self.session.flush()
        await self.session.refresh(mutation_db)

        return self._db_to_response(mutation_db)

    async def get_mutation(self, mutation_id: UUID) -> MutationResponse | None:
        """
        Get mutation by ID.

        Args:
            mutation_id: Mutation UUID

        Returns:
            Mutation response or None if not found
        """
        from app.swarm.models.mutation import MutationDB

        result = await self.session.execute(
            select(MutationDB).where(MutationDB.mutation_id == mutation_id)
        )
        mutation_db = result.scalar_one_or_none()

        if not mutation_db:
            return None

        return self._db_to_response(mutation_db)

    async def list_mutations(
        self,
        source_prompt_id: UUID | None = None,
        mutation_type: MutationType | str | None = None,
        state: MutationState | str | None = None,
        ab_test_active: bool | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[MutationResponse]:
        """
        List mutations with optional filtering.

        Args:
            source_prompt_id: Filter by source prompt
            mutation_type: Filter by mutation type
            state: Filter by state
            ab_test_active: Filter by A/B test active status
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of mutations
        """
        from app.swarm.models.mutation import MutationDB

        query = select(MutationDB)

        # Apply filters
        conditions = []
        if source_prompt_id:
            conditions.append(MutationDB.source_prompt_id == source_prompt_id)
        if mutation_type:
            mutation_type_value = mutation_type.value if isinstance(mutation_type, MutationType) else mutation_type
            conditions.append(MutationDB.mutation_type == mutation_type_value)
        if state:
            state_value = state.value if isinstance(state, MutationState) else state
            conditions.append(MutationDB.state == state_value)
        if ab_test_active is not None:
            conditions.append(MutationDB.ab_test_active == ab_test_active)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by created_at descending (newest first)
        query = query.order_by(desc(MutationDB.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        mutations = result.scalars().all()

        return [self._db_to_response(mutation) for mutation in mutations]

    async def get_mutation_history(self, prompt_id: UUID) -> list[MutationResponse]:
        """
        Get mutation history for a prompt (both as source and target).

        Args:
            prompt_id: Prompt UUID

        Returns:
            List of mutations involving this prompt
        """
        from app.swarm.models.mutation import MutationDB

        result = await self.session.execute(
            select(MutationDB)
            .where(
                (MutationDB.source_prompt_id == prompt_id) |
                (MutationDB.target_prompt_id == prompt_id)
            )
            .order_by(desc(MutationDB.created_at))
        )
        mutations = result.scalars().all()

        return [self._db_to_response(mutation) for mutation in mutations]

    async def start_ab_test(self, mutation_id: UUID) -> MutationResponse | None:
        """
        Start A/B testing for a mutation.

        Args:
            mutation_id: Mutation UUID

        Returns:
            Updated mutation response or None if not found
        """
        from app.swarm.models.mutation import MutationDB

        result = await self.session.execute(
            select(MutationDB).where(MutationDB.mutation_id == mutation_id)
        )
        mutation_db = result.scalar_one_or_none()

        if not mutation_db:
            return None

        mutation_db.ab_test_active = True
        mutation_db.state = "testing"
        mutation_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(mutation_db)

        return self._db_to_response(mutation_db)

    async def record_ab_result(
        self,
        mutation_id: UUID,
        variant: str,
        metrics: dict
    ) -> MutationResponse | None:
        """
        Record A/B test result.

        Args:
            mutation_id: Mutation UUID
            variant: Variant identifier (control or treatment)
            metrics: Result metrics

        Returns:
            Updated mutation response or None if not found
        """
        from app.swarm.models.mutation import MutationDB

        result = await self.session.execute(
            select(MutationDB).where(MutationDB.mutation_id == mutation_id)
        )
        mutation_db = result.scalar_one_or_none()

        if not mutation_db:
            return None

        # Initialize results if not present
        if mutation_db.ab_test_results is None:
            mutation_db.ab_test_results = {"variants": {}}

        # Record result for this variant
        mutation_db.ab_test_results["variants"][variant] = {
            **metrics,
            "recorded_at": datetime.utcnow().isoformat()
        }

        mutation_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(mutation_db)

        return self._db_to_response(mutation_db)

    async def update_mutation_state(
        self,
        mutation_id: UUID,
        state: MutationState | str
    ) -> MutationResponse | None:
        """
        Update mutation state.

        Args:
            mutation_id: Mutation UUID
            state: New state

        Returns:
            Updated mutation response or None if not found
        """
        from app.swarm.models.mutation import MutationDB

        state_value = state.value if isinstance(state, MutationState) else state

        result = await self.session.execute(
            select(MutationDB).where(MutationDB.mutation_id == mutation_id)
        )
        mutation_db = result.scalar_one_or_none()

        if not mutation_db:
            return None

        mutation_db.state = state_value
        mutation_db.updated_at = datetime.utcnow()

        # If approved, record deployment time
        if state_value == "deployed" and mutation_db.deployed_at is None:
            mutation_db.deployed_at = datetime.utcnow()
            mutation_db.ab_test_active = False

        await self.session.flush()
        await self.session.refresh(mutation_db)

        return self._db_to_response(mutation_db)

    async def stop_ab_test(self, mutation_id: UUID) -> MutationResponse | None:
        """
        Stop A/B testing for a mutation.

        Args:
            mutation_id: Mutation UUID

        Returns:
            Updated mutation response or None if not found
        """
        from app.swarm.models.mutation import MutationDB

        result = await self.session.execute(
            select(MutationDB).where(MutationDB.mutation_id == mutation_id)
        )
        mutation_db = result.scalar_one_or_none()

        if not mutation_db:
            return None

        mutation_db.ab_test_active = False
        mutation_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(mutation_db)

        return self._db_to_response(mutation_db)

    async def count_mutations(
        self,
        source_prompt_id: UUID | None = None,
        state: MutationState | str | None = None
    ) -> int:
        """
        Count mutations matching filters.

        Args:
            source_prompt_id: Filter by source prompt
            state: Filter by state

        Returns:
            Number of matching mutations
        """
        from app.swarm.models.mutation import MutationDB
        from sqlalchemy import func

        query = select(func.count(MutationDB.mutation_id))

        conditions = []
        if source_prompt_id:
            conditions.append(MutationDB.source_prompt_id == source_prompt_id)
        if state:
            state_value = state.value if isinstance(state, MutationState) else state
            conditions.append(MutationDB.state == state_value)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_mutation(self, mutation_id: UUID) -> bool:
        """
        Delete a mutation.

        Args:
            mutation_id: Mutation UUID

        Returns:
            True if deleted, False if not found
        """
        from app.swarm.models.mutation import MutationDB

        result = await self.session.execute(
            select(MutationDB).where(MutationDB.mutation_id == mutation_id)
        )
        mutation_db = result.scalar_one_or_none()

        if not mutation_db:
            return False

        await self.session.delete(mutation_db)
        await self.session.flush()

        return True

    def _db_to_response(self, mutation_db) -> MutationResponse:
        """Convert DB model to response model"""
        return MutationResponse(
            mutation_id=mutation_db.mutation_id,
            source_prompt_id=mutation_db.source_prompt_id,
            target_prompt_id=mutation_db.target_prompt_id,
            mutation_type=mutation_db.mutation_type,
            description=mutation_db.description,
            confidence=mutation_db.confidence,
            state=mutation_db.state,
            ab_test_active=mutation_db.ab_test_active,
            ab_test_results=mutation_db.ab_test_results,
            created_at=mutation_db.created_at,
            updated_at=mutation_db.updated_at,
            deployed_at=mutation_db.deployed_at
        )
