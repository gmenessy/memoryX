"""
Memory Card Repository - Data Access Layer for Memory Cards
"""
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryCardDB, MemoryCardCreate, MemoryCardUpdate, MemoryCardResponse


class MemoryRepository:
    """
    Repository for Memory Card operations.
    Supports CRUD operations with search and filtering.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, memory_data: MemoryCardCreate) -> MemoryCardResponse:
        """
        Create a new memory card.

        Args:
            memory_data: Memory card creation data

        Returns:
            Created memory card response
        """
        memory_db = MemoryCardDB(
            memory_type=memory_data.memory_type,
            title=memory_data.title,
            content=memory_data.content,
            confidence=memory_data.confidence,
            scope=memory_data.scope,
            source_events=memory_data.source_events
        )

        self.session.add(memory_db)
        await self.session.flush()
        await self.session.refresh(memory_db)

        return MemoryCardResponse(
            memory_id=memory_db.memory_id,
            memory_type=memory_db.memory_type,
            title=memory_db.title,
            content=memory_db.content,
            confidence=memory_db.confidence,
            scope=memory_db.scope,
            source_events=memory_db.source_events,
            created_at=memory_db.created_at,
            updated_at=memory_db.updated_at
        )

    async def get_by_id(self, memory_id: UUID) -> MemoryCardResponse | None:
        """
        Get memory card by ID.

        Args:
            memory_id: Memory card UUID

        Returns:
            Memory card response or None if not found
        """
        result = await self.session.execute(
            select(MemoryCardDB).where(MemoryCardDB.memory_id == memory_id)
        )
        memory_db = result.scalar_one_or_none()

        if not memory_db:
            return None

        return MemoryCardResponse(
            memory_id=memory_db.memory_id,
            memory_type=memory_db.memory_type,
            title=memory_db.title,
            content=memory_db.content,
            confidence=memory_db.confidence,
            scope=memory_db.scope,
            source_events=memory_db.source_events,
            created_at=memory_db.created_at,
            updated_at=memory_db.updated_at
        )

    async def update(self, memory_id: UUID, update_data: MemoryCardUpdate) -> MemoryCardResponse | None:
        """
        Update a memory card. Updates create new versions (evolution).

        Args:
            memory_id: Memory card UUID
            update_data: Update data

        Returns:
            Updated memory card response or None if not found
        """
        result = await self.session.execute(
            select(MemoryCardDB).where(MemoryCardDB.memory_id == memory_id)
        )
        memory_db = result.scalar_one_or_none()

        if not memory_db:
            return None

        # Update fields
        if update_data.title is not None:
            memory_db.title = update_data.title
        if update_data.content is not None:
            memory_db.content = update_data.content
        if update_data.confidence is not None:
            memory_db.confidence = update_data.confidence
        if update_data.scope is not None:
            memory_db.scope = update_data.scope

        memory_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(memory_db)

        return MemoryCardResponse(
            memory_id=memory_db.memory_id,
            memory_type=memory_db.memory_type,
            title=memory_db.title,
            content=memory_db.content,
            confidence=memory_db.confidence,
            scope=memory_db.scope,
            source_events=memory_db.source_events,
            created_at=memory_db.created_at,
            updated_at=memory_db.updated_at
        )

    async def list_memories(
        self,
        memory_type: str | None = None,
        scope: str | None = None,
        min_confidence: float | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[MemoryCardResponse]:
        """
        List memory cards with optional filtering.

        Args:
            memory_type: Filter by memory type
            scope: Filter by scope
            min_confidence: Minimum confidence score
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of memory cards
        """
        query = select(MemoryCardDB)

        # Apply filters
        conditions = []
        if memory_type:
            conditions.append(MemoryCardDB.memory_type == memory_type)
        if scope:
            conditions.append(MemoryCardDB.scope == scope)
        if min_confidence is not None:
            conditions.append(MemoryCardDB.confidence >= min_confidence)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by updated_at descending (most recently updated first)
        query = query.order_by(MemoryCardDB.updated_at.desc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        memories = result.scalars().all()

        return [
            MemoryCardResponse(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type,
                title=memory.title,
                content=memory.content,
                confidence=memory.confidence,
                scope=memory.scope,
                source_events=memory.source_events,
                created_at=memory.created_at,
                updated_at=memory.updated_at
            )
            for memory in memories
        ]

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
        search_conditions = [
            MemoryCardDB.title.ilike(f"%{query}%"),
            MemoryCardDB.content.ilike(f"%{query}%")
        ]

        conditions = [or_(*search_conditions)]

        if memory_type:
            conditions.append(MemoryCardDB.memory_type == memory_type)
        if scope:
            conditions.append(MemoryCardDB.scope == scope)

        db_query = select(MemoryCardDB).where(and_(*conditions))
        db_query = db_query.order_by(MemoryCardDB.updated_at.desc())
        db_query = db_query.limit(limit)

        result = await self.session.execute(db_query)
        memories = result.scalars().all()

        return [
            MemoryCardResponse(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type,
                title=memory.title,
                content=memory.content,
                confidence=memory.confidence,
                scope=memory.scope,
                source_events=memory.source_events,
                created_at=memory.created_at,
                updated_at=memory.updated_at
            )
            for memory in memories
        ]

    async def get_by_source_event(self, event_id: UUID) -> list[MemoryCardResponse]:
        """
        Get all memory cards derived from a specific event.

        Args:
            event_id: Source event ID

        Returns:
            List of memory cards
        """
        result = await self.session.execute(
            select(MemoryCardDB).where(
                MemoryCardDB.source_events.contains([event_id])
            )
        )
        memories = result.scalars().all()

        return [
            MemoryCardResponse(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type,
                title=memory.title,
                content=memory.content,
                confidence=memory.confidence,
                scope=memory.scope,
                source_events=memory.source_events,
                created_at=memory.created_at,
                updated_at=memory.updated_at
            )
            for memory in memories
        ]

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
            Number of matching memory cards
        """
        from sqlalchemy import func

        query = select(func.count(MemoryCardDB.memory_id))

        conditions = []
        if memory_type:
            conditions.append(MemoryCardDB.memory_type == memory_type)
        if scope:
            conditions.append(MemoryCardDB.scope == scope)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0