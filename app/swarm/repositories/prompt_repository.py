"""
Prompt Repository - Data Access Layer for Prompt Operations
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.swarm.models.prompt import (
    Prompt,
    PromptCreate,
    PromptResponse,
    PromptState,
    PromptType,
)


class PromptRepository:
    """
    Repository for Prompt operations.
    Manages prompt storage, versioning, and health tracking.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_prompt(self, prompt_data: PromptCreate) -> PromptResponse:
        """
        Create a new prompt.

        Args:
            prompt_data: Prompt creation data

        Returns:
            Created prompt response
        """
        from app.swarm.models.prompt import PromptDB

        # Check if there's an existing active prompt with this name
        existing = await self.get_active_prompt_by_name(prompt_data.name)

        prompt_db = PromptDB(
            name=prompt_data.name,
            version=(existing.version + 1 if existing else 1),
            content=prompt_data.content,
            prompt_type=prompt_data.prompt_type.value if isinstance(prompt_data.prompt_type, PromptType) else prompt_data.prompt_type,
            purpose=prompt_data.purpose,
            tags=prompt_data.tags,
            metadata=prompt_data.metadata,
            is_active=not bool(existing),  # Only active if no existing active prompt
            state="draft" if existing else "active"
        )

        # Link to parent if existing
        if existing:
            prompt_db.parent_prompt_id = existing.prompt_id

        self.session.add(prompt_db)
        await self.session.flush()
        await self.session.refresh(prompt_db)

        return PromptResponse(
            prompt_id=prompt_db.prompt_id,
            name=prompt_db.name,
            version=prompt_db.version,
            content=prompt_db.content,
            prompt_type=prompt_db.prompt_type,
            purpose=prompt_db.purpose,
            tags=prompt_db.tags,
            metadata=prompt_db.metadata,
            health_score=prompt_db.health_score,
            usage_count=prompt_db.usage_count,
            success_rate=prompt_db.success_rate,
            avg_response_time=prompt_db.avg_response_time,
            parent_prompt_id=prompt_db.parent_prompt_id,
            is_active=prompt_db.is_active,
            state=prompt_db.state,
            created_at=prompt_db.created_at,
            updated_at=prompt_db.updated_at,
            last_evaluation=prompt_db.last_evaluation
        )

    async def get_prompt(self, prompt_id: UUID) -> PromptResponse | None:
        """
        Get prompt by ID.

        Args:
            prompt_id: Prompt UUID

        Returns:
            Prompt response or None if not found
        """
        from app.swarm.models.prompt import PromptDB

        result = await self.session.execute(
            select(PromptDB).where(PromptDB.prompt_id == prompt_id)
        )
        prompt_db = result.scalar_one_or_none()

        if not prompt_db:
            return None

        return self._db_to_response(prompt_db)

    async def get_active_prompt_by_name(self, name: str) -> PromptResponse | None:
        """
        Get active prompt by name.

        Args:
            name: Prompt name

        Returns:
            Active prompt response or None if not found
        """
        from app.swarm.models.prompt import PromptDB

        result = await self.session.execute(
            select(PromptDB)
            .where(PromptDB.name == name)
            .where(PromptDB.is_active == True)
            .order_by(desc(PromptDB.version))
            .limit(1)
        )
        prompt_db = result.scalar_one_or_none()

        if not prompt_db:
            return None

        return self._db_to_response(prompt_db)

    async def list_prompts(
        self,
        prompt_type: PromptType | str | None = None,
        is_active: bool | None = None,
        state: PromptState | str | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[PromptResponse]:
        """
        List prompts with optional filtering.

        Args:
            prompt_type: Filter by prompt type
            is_active: Filter by active status
            state: Filter by state
            tags: Filter by tags (any match)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of prompts
        """
        from app.swarm.models.prompt import PromptDB

        query = select(PromptDB)

        # Apply filters
        conditions = []
        if prompt_type:
            prompt_type_value = prompt_type.value if isinstance(prompt_type, PromptType) else prompt_type
            conditions.append(PromptDB.prompt_type == prompt_type_value)
        if is_active is not None:
            conditions.append(PromptDB.is_active == is_active)
        if state:
            state_value = state.value if isinstance(state, PromptState) else state
            conditions.append(PromptDB.state == state_value)
        if tags:
            # Check if any of the tags match
            conditions.append(PromptDB.tags.overlap(tags))

        if conditions:
            query = query.where(and_(*conditions))

        # Order by created_at descending (newest first)
        query = query.order_by(desc(PromptDB.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        prompts = result.scalars().all()

        return [self._db_to_response(prompt) for prompt in prompts]

    async def get_prompt_history(self, name: str, limit: int = 10) -> list[PromptResponse]:
        """
        Get version history for a prompt.

        Args:
            name: Prompt name
            limit: Maximum number of versions

        Returns:
            List of prompt versions ordered by version descending
        """
        from app.swarm.models.prompt import PromptDB

        result = await self.session.execute(
            select(PromptDB)
            .where(PromptDB.name == name)
            .order_by(desc(PromptDB.version))
            .limit(limit)
        )
        prompts = result.scalars().all()

        return [self._db_to_response(prompt) for prompt in prompts]

    async def update_prompt_health(
        self,
        prompt_id: UUID,
        success: bool,
        response_time: float
    ) -> PromptResponse | None:
        """
        Update prompt health metrics.

        Args:
            prompt_id: Prompt UUID
            success: Whether the usage was successful
            response_time: Response time in seconds

        Returns:
            Updated prompt response or None if not found
        """
        from app.swarm.models.prompt import PromptDB

        result = await self.session.execute(
            select(PromptDB).where(PromptDB.prompt_id == prompt_id)
        )
        prompt_db = result.scalar_one_or_none()

        if not prompt_db:
            return None

        # Update metrics
        prompt_db.usage_count += 1
        prompt_db.last_evaluation = datetime.utcnow()

        # Calculate new success rate (exponential moving average)
        alpha = 0.1  # Smoothing factor
        if success:
            new_success = 1.0
        else:
            new_success = 0.0
        prompt_db.success_rate = (alpha * new_success) + ((1 - alpha) * prompt_db.success_rate)

        # Calculate new average response time
        prompt_db.avg_response_time = (alpha * response_time) + ((1 - alpha) * prompt_db.avg_response_time)

        # Calculate health score (combination of success rate and response time)
        # Higher success rate and lower response time = higher health
        response_time_score = max(0, 1 - (response_time / 10.0))  # 10 seconds is baseline
        prompt_db.health_score = (0.7 * prompt_db.success_rate) + (0.3 * response_time_score)

        await self.session.flush()
        await self.session.refresh(prompt_db)

        return self._db_to_response(prompt_db)

    async def activate_prompt(self, prompt_id: UUID) -> PromptResponse | None:
        """
        Activate a prompt version (deactivate others with same name).

        Args:
            prompt_id: Prompt UUID

        Returns:
            Updated prompt response or None if not found
        """
        from app.swarm.models.prompt import PromptDB

        # Get the prompt to activate
        result = await self.session.execute(
            select(PromptDB).where(PromptDB.prompt_id == prompt_id)
        )
        prompt_db = result.scalar_one_or_none()

        if not prompt_db:
            return None

        # Deactivate all prompts with the same name
        await self.session.execute(
            select(PromptDB)
            .where(PromptDB.name == prompt_db.name)
            .where(PromptDB.prompt_id != prompt_id)
        )

        # Update all with same name
        from sqlalchemy import update
        await self.session.execute(
            update(PromptDB)
            .where(PromptDB.name == prompt_db.name)
            .where(PromptDB.prompt_id != prompt_id)
            .values(is_active=False, state="deprecated")
        )

        # Activate the target prompt
        prompt_db.is_active = True
        prompt_db.state = "active"
        prompt_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(prompt_db)

        return self._db_to_response(prompt_db)

    async def search_prompts(
        self,
        query: str,
        prompt_type: PromptType | str | None = None,
        min_health_score: float | None = None,
        limit: int = 50
    ) -> list[PromptResponse]:
        """
        Search prompts by content, name, or purpose.

        Args:
            query: Search query
            prompt_type: Optional filter by prompt type
            min_health_score: Minimum health score
            limit: Maximum number of results

        Returns:
            List of matching prompts
        """
        from app.swarm.models.prompt import PromptDB

        # Use ILIKE for case-insensitive search
        search_pattern = f"%{query}%"

        db_query = select(PromptDB).where(
            (PromptDB.name.ilike(search_pattern)) |
            (PromptDB.content.ilike(search_pattern)) |
            (PromptDB.purpose.ilike(search_pattern))
        )

        # Apply additional filters
        if prompt_type:
            prompt_type_value = prompt_type.value if isinstance(prompt_type, PromptType) else prompt_type
            db_query = db_query.where(PromptDB.prompt_type == prompt_type_value)

        if min_health_score is not None:
            db_query = db_query.where(PromptDB.health_score >= min_health_score)

        # Order by health score descending
        db_query = db_query.order_by(desc(PromptDB.health_score))
        db_query = db_query.limit(limit)

        result = await self.session.execute(db_query)
        prompts = result.scalars().all()

        return [self._db_to_response(prompt) for prompt in prompts]

    async def delete_prompt(self, prompt_id: UUID) -> bool:
        """
        Delete a prompt.

        Args:
            prompt_id: Prompt UUID

        Returns:
            True if deleted, False if not found
        """
        from app.swarm.models.prompt import PromptDB

        result = await self.session.execute(
            select(PromptDB).where(PromptDB.prompt_id == prompt_id)
        )
        prompt_db = result.scalar_one_or_none()

        if not prompt_db:
            return False

        await self.session.delete(prompt_db)
        await self.session.flush()

        return True

    async def count_prompts(
        self,
        prompt_type: PromptType | str | None = None,
        is_active: bool | None = None
    ) -> int:
        """
        Count prompts matching filters.

        Args:
            prompt_type: Filter by prompt type
            is_active: Filter by active status

        Returns:
            Number of matching prompts
        """
        from app.swarm.models.prompt import PromptDB
        from sqlalchemy import func

        query = select(func.count(PromptDB.prompt_id))

        conditions = []
        if prompt_type:
            prompt_type_value = prompt_type.value if isinstance(prompt_type, PromptType) else prompt_type
            conditions.append(PromptDB.prompt_type == prompt_type_value)
        if is_active is not None:
            conditions.append(PromptDB.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    def _db_to_response(self, prompt_db) -> PromptResponse:
        """Convert DB model to response model"""
        return PromptResponse(
            prompt_id=prompt_db.prompt_id,
            name=prompt_db.name,
            version=prompt_db.version,
            content=prompt_db.content,
            prompt_type=prompt_db.prompt_type,
            purpose=prompt_db.purpose,
            tags=prompt_db.tags,
            metadata=prompt_db.metadata,
            health_score=prompt_db.health_score,
            usage_count=prompt_db.usage_count,
            success_rate=prompt_db.success_rate,
            avg_response_time=prompt_db.avg_response_time,
            parent_prompt_id=prompt_db.parent_prompt_id,
            is_active=prompt_db.is_active,
            state=prompt_db.state,
            created_at=prompt_db.created_at,
            updated_at=prompt_db.updated_at,
            last_evaluation=prompt_db.last_evaluation
        )
