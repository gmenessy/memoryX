"""
Evolution Service - Business Logic Layer for Memory Evolution
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolution import (
    MemoryPatchCreate,
    MemoryPatchResponse,
    MemoryEvolutionHistory,
    PATCH_TYPES,
    MEMORY_STATES
)
from app.models.memory import MemoryCardDB
from app.repositories.evolution_repository import EvolutionRepository
from app.repositories.memory_repository import MemoryRepository


class EvolutionService:
    """
    Service layer for Memory Evolution operations.
    Handles business logic and validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.evolution_repo = EvolutionRepository(session)
        self.memory_repo = MemoryRepository(session)

    async def create_patch(self, patch_data: MemoryPatchCreate) -> MemoryPatchResponse:
        """
        Create a new memory patch with validation.

        Args:
            patch_data: Patch creation data

        Returns:
            Created patch response

        Raises:
            ValueError: If validation fails
        """
        # Validate patch type
        if patch_data.patch_type not in PATCH_TYPES:
            raise ValueError(
                f"Invalid patch type: {patch_data.patch_type}. "
                f"Must be one of: {', '.join(PATCH_TYPES)}"
            )

        # Validate target memory exists
        memory = await self.memory_repo.get_by_id(patch_data.target_memory)
        if not memory:
            raise ValueError(f"Target memory {patch_data.target_memory} not found")

        # Validate confidence range
        if not 0.0 <= patch_data.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        # Validate reason
        if not patch_data.reason.strip():
            raise ValueError("Reason cannot be empty")

        # Create patch via repository
        return await self.evolution_repo.create_patch(patch_data)

    async def get_patch(self, patch_id: UUID) -> MemoryPatchResponse | None:
        """
        Get patch by ID.

        Args:
            patch_id: Patch UUID

        Returns:
            Patch response or None
        """
        return await self.evolution_repo.get_patch(patch_id)

    async def get_patches_for_memory(
        self,
        memory_id: UUID,
        limit: int = 100
    ) -> list[MemoryPatchResponse]:
        """
        Get all patches for a specific memory.

        Args:
            memory_id: Memory card UUID
            limit: Maximum number of results

        Returns:
            List of patches
        """
        # Validate memory exists
        memory = await self.memory_repo.get_by_id(memory_id)
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")

        return await self.evolution_repo.get_patches_for_memory(memory_id, limit)

    async def list_patches(
        self,
        patch_type: str | None = None,
        target_memory: UUID | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[MemoryPatchResponse]:
        """
        List patches with filtering and pagination.

        Args:
            patch_type: Filter by patch type
            target_memory: Filter by target memory
            limit: Max results
            offset: Pagination offset

        Returns:
            List of patches
        """
        # Validate limit
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.evolution_repo.list_patches(
            patch_type=patch_type,
            target_memory=target_memory,
            limit=limit,
            offset=offset
        )

    async def count_patches(
        self,
        patch_type: str | None = None,
        target_memory: UUID | None = None
    ) -> int:
        """
        Count patches matching filters.

        Args:
            patch_type: Filter by patch type
            target_memory: Filter by target memory

        Returns:
            Patch count
        """
        return await self.evolution_repo.count_patches(
            patch_type=patch_type,
            target_memory=target_memory
        )

    async def get_memory_evolution_history(
        self,
        memory_id: UUID
    ) -> MemoryEvolutionHistory:
        """
        Get complete evolution history for a memory.

        Args:
            memory_id: Memory card UUID

        Returns:
            Evolution history with fitness score

        Raises:
            ValueError: If memory not found
        """
        history = await self.evolution_repo.get_memory_with_history(memory_id)

        if not history:
            raise ValueError(f"Memory {memory_id} not found")

        return MemoryEvolutionHistory(**history)

    async def promote_memory(
        self,
        memory_id: UUID,
        reason: str,
        confidence: float = 0.8
    ) -> MemoryPatchResponse:
        """
        Promote a memory (e.g., from candidate to active).

        Args:
            memory_id: Memory to promote
            reason: Reason for promotion
            confidence: Confidence in promotion

        Returns:
            Created patch

        Raises:
            ValueError: If validation fails
        """
        # Get current memory state
        memory = await self.memory_repo.get_by_id(memory_id)
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")

        # Create promotion patch
        patch_data = MemoryPatchCreate(
            target_memory=memory_id,
            patch_type="promotion",
            old_value={"state": "candidate"},
            new_value={"state": "active"},
            reason=reason,
            confidence=confidence
        )

        return await self.create_patch(patch_data)

    async def deprecate_memory(
        self,
        memory_id: UUID,
        reason: str,
        replacement_memory: UUID | None = None
    ) -> MemoryPatchResponse:
        """
        Deprecate a memory.

        Args:
            memory_id: Memory to deprecate
            reason: Reason for deprecation
            replacement_memory: Optional replacement memory ID

        Returns:
            Created patch

        Raises:
            ValueError: If validation fails
        """
        # Get current memory state
        memory = await self.memory_repo.get_by_id(memory_id)
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")

        # Create deprecation patch
        old_value = {"state": "active"}
        new_value = {
            "state": "deprecated",
            "replacement_memory": str(replacement_memory) if replacement_memory else None
        }

        patch_data = MemoryPatchCreate(
            target_memory=memory_id,
            patch_type="deprecate",
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            confidence=0.9
        )

        return await self.create_patch(patch_data)

    async def merge_memories(
        self,
        source_memories: list[UUID],
        target_memory: UUID,
        reason: str,
        confidence: float = 0.7
    ) -> MemoryPatchResponse:
        """
        Merge multiple memories into one.

        Args:
            source_memories: List of source memory IDs to merge
            target_memory: Target memory ID (will contain merged result)
            reason: Reason for merge
            confidence: Confidence in merge quality

        Returns:
            Created patch

        Raises:
            ValueError: If validation fails
        """
        # Validate all memories exist
        for memory_id in source_memories:
            memory = await self.memory_repo.get_by_id(memory_id)
            if not memory:
                raise ValueError(f"Source memory {memory_id} not found")

        # Validate target memory exists
        target = await self.memory_repo.get_by_id(target_memory)
        if not target:
            raise ValueError(f"Target memory {target_memory} not found")

        # Create merge patch
        patch_data = MemoryPatchCreate(
            target_memory=target_memory,
            patch_type="merge",
            old_value={"source_memories": [str(m) for m in source_memories]},
            new_value={"merged_from": [str(m) for m in source_memories]},
            reason=reason,
            confidence=confidence
        )

        return await self.create_patch(patch_data)

    async def get_evolution_statistics(
        self,
        scope: str | None = None
    ) -> dict:
        """
        Get evolution system statistics.

        Args:
            scope: Filter by scope

        Returns:
            Statistics dictionary
        """
        total_patches = await self.count_patches()

        # Count by patch type
        patch_type_counts = {}
        for patch_type in PATCH_TYPES:
            count = await self.count_patches(patch_type=patch_type)
            patch_type_counts[patch_type] = count

        return {
            "total_patches": total_patches,
            "by_patch_type": patch_type_counts,
            "available_patch_types": PATCH_TYPES,
            "memory_states": MEMORY_STATES
        }