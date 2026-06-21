"""
Prompt Service - Business Logic Layer for Prompt Operations
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.models.prompt import (
    Prompt,
    PromptCreate,
    PromptHealth,
    PromptResponse,
    PromptSearchParams,
    PromptState,
    PromptType,
    PromptUpdate,
)
from app.swarm.repositories.prompt_repository import PromptRepository


class PromptService:
    """
    Service layer for Prompt operations.
    Handles prompt versioning, health tracking, and business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PromptRepository(session)

    async def create_prompt(self, prompt_data: PromptCreate) -> PromptResponse:
        """
        Create a new prompt with validation.

        Args:
            prompt_data: Prompt creation data

        Returns:
            Created prompt response

        Raises:
            ValueError: If prompt data is invalid
        """
        # Validate prompt name
        if not prompt_data.name or not prompt_data.name.strip():
            raise ValueError("Prompt name is required")

        # Validate content
        if not prompt_data.content or not prompt_data.content.strip():
            raise ValueError("Prompt content is required")

        # Validate purpose
        if not prompt_data.purpose or not prompt_data.purpose.strip():
            raise ValueError("Prompt purpose is required")

        # Create prompt via repository
        return await self.repository.create_prompt(prompt_data)

    async def get_prompt(self, prompt_id: UUID) -> PromptResponse | None:
        """
        Get prompt by ID.

        Args:
            prompt_id: Prompt UUID

        Returns:
            Prompt response or None
        """
        return await self.repository.get_prompt(prompt_id)

    async def get_active_prompt(self, name: str) -> PromptResponse | None:
        """
        Get active prompt by name.

        Args:
            name: Prompt name

        Returns:
            Active prompt response or None
        """
        return await self.repository.get_active_prompt_by_name(name)

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
        List prompts with filtering and pagination.

        Args:
            prompt_type: Filter by prompt type
            is_active: Filter by active status
            state: Filter by state
            tags: Filter by tags
            limit: Max results
            offset: Pagination offset

        Returns:
            List of prompts
        """
        # Validate limit
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.repository.list_prompts(
            prompt_type=prompt_type,
            is_active=is_active,
            state=state,
            tags=tags,
            limit=limit,
            offset=offset
        )

    async def update_prompt(
        self,
        prompt_id: UUID,
        prompt_data: PromptUpdate
    ) -> PromptResponse | None:
        """
        Update prompt properties.

        Args:
            prompt_id: Prompt UUID
            prompt_data: Update data

        Returns:
            Updated prompt response or None
        """
        # Get current prompt
        prompt = await self.repository.get_prompt(prompt_id)
        if not prompt:
            return None

        # Create a new version if content changed
        if prompt_data.content and prompt_data.content != prompt.content:
            new_prompt = PromptCreate(
                name=prompt.name,
                content=prompt_data.content,
                prompt_type=PromptType(prompt.prompt_type),
                purpose=prompt_data.purpose or prompt.purpose,
                tags=prompt_data.tags or prompt.tags,
                metadata=prompt.metadata
            )
            return await self.repository.create_prompt(new_prompt)

        # Otherwise update metadata
        from sqlalchemy import update
        from app.swarm.models.prompt import PromptDB

        update_values = {"updated_at": datetime.utcnow()}
        if prompt_data.purpose:
            update_values["purpose"] = prompt_data.purpose
        if prompt_data.tags:
            update_values["tags"] = prompt_data.tags
        if prompt_data.metadata:
            update_values["metadata"] = prompt_data.metadata

        await self.session.execute(
            update(PromptDB)
            .where(PromptDB.prompt_id == prompt_id)
            .values(**update_values)
        )
        await self.session.flush()

        return await self.repository.get_prompt(prompt_id)

    async def activate_prompt(self, prompt_id: UUID) -> PromptResponse | None:
        """
        Activate a prompt version.

        Args:
            prompt_id: Prompt UUID

        Returns:
            Updated prompt response or None
        """
        return await self.repository.activate_prompt(prompt_id)

    async def update_prompt_health(
        self,
        prompt_id: UUID,
        health: PromptHealth
    ) -> PromptResponse | None:
        """
        Update prompt health metrics.

        Args:
            prompt_id: Prompt UUID
            health: Health update data

        Returns:
            Updated prompt response or None
        """
        return await self.repository.update_prompt_health(
            prompt_id,
            health.success,
            health.response_time
        )

    async def record_usage(
        self,
        prompt_id: UUID,
        success: bool,
        response_time: float
    ) -> PromptResponse | None:
        """
        Record prompt usage.

        Args:
            prompt_id: Prompt UUID
            success: Whether usage was successful
            response_time: Response time in seconds

        Returns:
            Updated prompt response or None
        """
        return await self.repository.update_prompt_health(prompt_id, success, response_time)

    async def get_prompt_history(self, prompt_id: UUID) -> list[PromptResponse]:
        """
        Get version history for a prompt.

        Args:
            prompt_id: Prompt UUID

        Returns:
            List of prompt versions
        """
        prompt = await self.repository.get_prompt(prompt_id)
        if not prompt:
            return []

        return await self.repository.get_prompt_history(prompt.name)

    async def search_prompts(self, search_params: PromptSearchParams) -> list[PromptResponse]:
        """
        Search prompts by query.

        Args:
            search_params: Search parameters

        Returns:
            List of matching prompts
        """
        return await self.repository.search_prompts(
            query=search_params.query or "",
            prompt_type=search_params.prompt_type,
            min_health_score=search_params.min_health_score,
            limit=search_params.limit
        )

    async def delete_prompt(self, prompt_id: UUID) -> bool:
        """
        Delete a prompt.

        Args:
            prompt_id: Prompt UUID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_prompt(prompt_id)

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
        return await self.repository.count_prompts(prompt_type, is_active)
