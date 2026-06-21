"""
Memory Service - Business Logic Layer for Memory Cards
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryCardCreate, MemoryCardUpdate, MemoryCardResponse, MEMORY_TYPES
from app.repositories.memory_repository import MemoryRepository


class MemoryService:
    """
    Service layer for Memory Card operations.
    Handles business logic and validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = MemoryRepository(session)

    async def create_memory(self, memory_data: MemoryCardCreate) -> MemoryCardResponse:
        """
        Create a new memory card with validation.

        Args:
            memory_data: Memory card creation data

        Returns:
            Created memory card response

        Raises:
            ValueError: If validation fails
        """
        # Validate memory type
        if memory_data.memory_type not in MEMORY_TYPES:
            raise ValueError(
                f"Invalid memory type: {memory_data.memory_type}. "
                f"Must be one of: {', '.join(MEMORY_TYPES)}"
            )

        # Validate confidence range
        if not 0.0 <= memory_data.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        # Validate required fields
        if not memory_data.title.strip():
            raise ValueError("Title cannot be empty")

        if not memory_data.content.strip():
            raise ValueError("Content cannot be empty")

        if not memory_data.scope:
            raise ValueError("Scope is required")

        # Create memory via repository
        return await self.repository.create(memory_data)

    async def get_memory(self, memory_id: UUID) -> MemoryCardResponse | None:
        """
        Get memory card by ID.

        Args:
            memory_id: Memory card UUID

        Returns:
            Memory card response or None
        """
        return await self.repository.get_by_id(memory_id)

    async def update_memory(
        self,
        memory_id: UUID,
        update_data: MemoryCardUpdate
    ) -> MemoryCardResponse | None:
        """
        Update a memory card.

        Args:
            memory_id: Memory card UUID
            update_data: Update data

        Returns:
            Updated memory card response or None

        Raises:
            ValueError: If validation fails
        """
        # Validate confidence range if provided
        if update_data.confidence is not None and not 0.0 <= update_data.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        # Validate title if provided
        if update_data.title is not None and not update_data.title.strip():
            raise ValueError("Title cannot be empty")

        # Validate content if provided
        if update_data.content is not None and not update_data.content.strip():
            raise ValueError("Content cannot be empty")

        return await self.repository.update(memory_id, update_data)

    async def list_memories(
        self,
        memory_type: str | None = None,
        scope: str | None = None,
        min_confidence: float | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[MemoryCardResponse]:
        """
        List memory cards with filtering and pagination.

        Args:
            memory_type: Filter by memory type
            scope: Filter by scope
            min_confidence: Minimum confidence score
            limit: Max results
            offset: Pagination offset

        Returns:
            List of memory cards
        """
        # Validate limit
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.repository.list_memories(
            memory_type=memory_type,
            scope=scope,
            min_confidence=min_confidence,
            limit=limit,
            offset=offset
        )

    async def search_memories(
        self,
        query: str,
        memory_type: str | None = None,
        scope: str | None = None,
        limit: int = 100
    ) -> list[MemoryCardResponse]:
        """
        Search memory cards by title and content.

        Args:
            query: Search query string
            memory_type: Filter by memory type
            scope: Filter by scope
            limit: Maximum number of results

        Returns:
            List of matching memory cards
        """
        if not query.strip():
            raise ValueError("Search query cannot be empty")

        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        return await self.repository.search_memories(
            query=query,
            memory_type=memory_type,
            scope=scope,
            limit=limit
        )

    async def get_by_source_event(self, event_id: UUID) -> list[MemoryCardResponse]:
        """
        Get all memory cards derived from a specific event.

        Args:
            event_id: Source event ID

        Returns:
            List of memory cards
        """
        return await self.repository.get_by_source_event(event_id)

    async def count_memories(
        self,
        memory_type: str | None = None,
        scope: str | None = None
    ) -> int:
        """
        Count memory cards matching filters.

        Args:
            memory_type: Filter by memory type
            scope: Filter by scope

        Returns:
            Memory card count
        """
        return await self.repository.count_memories(
            memory_type=memory_type,
            scope=scope
        )

    async def get_memory_statistics(
        self,
        scope: str | None = None
    ) -> dict:
        """
        Get statistics about memory cards.

        Args:
            scope: Filter by scope

        Returns:
            Statistics dictionary
        """
        total_count = await self.count_memories(scope=scope)

        # Count by memory type
        memory_type_counts = {}
        for memory_type in MEMORY_TYPES:
            count = await self.count_memories(
                memory_type=memory_type,
                scope=scope
            )
            memory_type_counts[memory_type] = count

        return {
            "total_memories": total_count,
            "by_memory_type": memory_type_counts,
            "scope": scope or "all"
        }