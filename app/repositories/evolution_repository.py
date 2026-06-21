"""
Evolution Memory Repository - Data Access Layer for Memory Evolution
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evolution import MemoryPatchDB, MemoryPatchCreate, MemoryPatchResponse
from app.models.memory import MemoryCardDB


class EvolutionRepository:
    """
    Repository for Memory Evolution operations.
    Manages memory patches and evolution tracking.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_patch(self, patch_data: MemoryPatchCreate) -> MemoryPatchResponse:
        """
        Create a new memory patch.

        Args:
            patch_data: Patch creation data

        Returns:
            Created patch response
        """
        patch_db = MemoryPatchDB(
            target_memory=patch_data.target_memory,
            patch_type=patch_data.patch_type,
            old_value=patch_data.old_value,
            new_value=patch_data.new_value,
            reason=patch_data.reason,
            confidence=patch_data.confidence
        )

        self.session.add(patch_db)
        await self.session.flush()
        await self.session.refresh(patch_db)

        return MemoryPatchResponse(
            patch_id=patch_db.patch_id,
            target_memory=patch_db.target_memory,
            patch_type=patch_db.patch_type,
            old_value=patch_db.old_value,
            new_value=patch_db.new_value,
            reason=patch_db.reason,
            confidence=patch_db.confidence,
            created_at=patch_db.created_at
        )

    async def get_patch(self, patch_id: UUID) -> MemoryPatchResponse | None:
        """
        Get patch by ID.

        Args:
            patch_id: Patch UUID

        Returns:
            Patch response or None if not found
        """
        result = await self.session.execute(
            select(MemoryPatchDB).where(MemoryPatchDB.patch_id == patch_id)
        )
        patch_db = result.scalar_one_or_none()

        if not patch_db:
            return None

        return MemoryPatchResponse(
            patch_id=patch_db.patch_id,
            target_memory=patch_db.target_memory,
            patch_type=patch_db.patch_type,
            old_value=patch_db.old_value,
            new_value=patch_db.new_value,
            reason=patch_db.reason,
            confidence=patch_db.confidence,
            created_at=patch_db.created_at
        )

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
            List of patches ordered by creation time
        """
        result = await self.session.execute(
            select(MemoryPatchDB)
            .where(MemoryPatchDB.target_memory == memory_id)
            .order_by(desc(MemoryPatchDB.created_at))
            .limit(limit)
        )
        patches = result.scalars().all()

        return [
            MemoryPatchResponse(
                patch_id=patch.patch_id,
                target_memory=patch.target_memory,
                patch_type=patch.patch_type,
                old_value=patch.old_value,
                new_value=patch.new_value,
                reason=patch.reason,
                confidence=patch.confidence,
                created_at=patch.created_at
            )
            for patch in patches
        ]

    async def list_patches(
        self,
        patch_type: str | None = None,
        target_memory: UUID | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[MemoryPatchResponse]:
        """
        List patches with optional filtering.

        Args:
            patch_type: Filter by patch type
            target_memory: Filter by target memory
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of patches
        """
        query = select(MemoryPatchDB)

        # Apply filters
        conditions = []
        if patch_type:
            conditions.append(MemoryPatchDB.patch_type == patch_type)
        if target_memory:
            conditions.append(MemoryPatchDB.target_memory == target_memory)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by created_at descending (newest first)
        query = query.order_by(desc(MemoryPatchDB.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        patches = result.scalars().all()

        return [
            MemoryPatchResponse(
                patch_id=patch.patch_id,
                target_memory=patch.target_memory,
                patch_type=patch.patch_type,
                old_value=patch.old_value,
                new_value=patch.new_value,
                reason=patch.reason,
                confidence=patch.confidence,
                created_at=patch.created_at
            )
            for patch in patches
        ]

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
            Number of matching patches
        """
        from sqlalchemy import func

        query = select(func.count(MemoryPatchDB.patch_id))

        conditions = []
        if patch_type:
            conditions.append(MemoryPatchDB.patch_type == patch_type)
        if target_memory:
            conditions.append(MemoryPatchDB.target_memory == target_memory)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_memory_with_history(self, memory_id: UUID) -> dict:
        """
        Get memory with its complete evolution history.

        Args:
            memory_id: Memory card UUID

        Returns:
            Dictionary with memory info and patch history
        """
        # Get current memory state
        result = await self.session.execute(
            select(MemoryCardDB).where(MemoryCardDB.memory_id == memory_id)
        )
        memory_db = result.scalar_one_or_none()

        if not memory_db:
            return None

        # Get patches
        patches = await self.get_patches_for_memory(memory_id)

        # Calculate fitness score
        fitness_score = self._calculate_fitness_score(memory_db, patches)

        return {
            "memory_id": memory_id,
            "current_state": {
                "memory_type": memory_db.memory_type,
                "title": memory_db.title,
                "content": memory_db.content,
                "confidence": memory_db.confidence,
                "scope": memory_db.scope,
                "source_events": memory_db.source_events,
                "created_at": memory_db.created_at.isoformat(),
                "updated_at": memory_db.updated_at.isoformat()
            },
            "total_patches": len(patches),
            "patches": patches,
            "fitness_score": fitness_score
        }

    def _calculate_fitness_score(
        self,
        memory_db: MemoryCardDB,
        patches: list
    ) -> float:
        """
        Calculate fitness score for a memory.

        Formula: fitness = usage * success_rate * confidence * recency

        Args:
            memory_db: Memory database object
            patches: List of patches

        Returns:
            Fitness score (0-1)
        """
        # Base confidence
        confidence = memory_db.confidence

        # Usage factor: more patches = more usage/evolution
        # Normalize to 0-1 range (assuming max 100 patches is high usage)
        usage = min(len(patches) / 100.0, 1.0)

        # Success rate: recent patches with high confidence
        if patches:
            recent_confidence = sum(patch.confidence for patch in patches[:5]) / min(len(patches), 5)
            success_rate = recent_confidence
        else:
            success_rate = 0.5  # Default for new memories

        # Recency factor: recently updated memories score higher
        days_since_update = (datetime.utcnow() - memory_db.updated_at).days
        # Decay over 90 days
        recency = max(0, 1.0 - (days_since_update / 90.0))

        # Calculate fitness
        fitness = usage * success_rate * confidence * recency

        return min(max(fitness, 0.0), 1.0)  # Ensure 0-1 range