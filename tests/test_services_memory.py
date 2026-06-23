"""
Unit Tests for MemoryService.

Tests the business logic layer for Memory Card operations.
Uses mocked repositories to isolate the service layer.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.constants import CONFIDENCE_MAX, CONFIDENCE_MIN, MAX_LIMIT, MIN_LIMIT, MIN_OFFSET
from app.exceptions import NotFoundError, ValidationError
from app.models.memory import (
    MemoryCardCreate,
    MemoryCardUpdate,
    MemoryCardResponse,
    MEMORY_TYPES,
)
from app.services.memory_service import MemoryService


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_repository():
    """Create a mock MemoryRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def memory_service(mock_session, mock_repository):
    """Create MemoryService with mocked dependencies."""
    service = MemoryService(mock_session)
    service.repository = mock_repository
    return service


@pytest.fixture
def sample_memory_data():
    """Create sample memory card data."""
    return MemoryCardCreate(
        memory_type="episodic",
        title="Test Memory",
        content="Test content",
        confidence=0.8,
        scope="test_scope",
        source_events=[],
    )


class TestMemoryServiceCreate:
    """Tests for create_memory method."""

    async def test_create_memory_success(self, memory_service, mock_repository, sample_memory_data):
        """Test successful memory creation."""
        # Setup
        expected_response = MemoryCardResponse(
            memory_id=uuid4(),
            memory_type="episodic",
            title="Test Memory",
            content="Test content",
            confidence=0.8,
            scope="test_scope",
            source_events=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.create.return_value = expected_response

        # Execute
        result = await memory_service.create_memory(sample_memory_data)

        # Verify
        assert result == expected_response
        mock_repository.create.assert_called_once_with(sample_memory_data)

    async def test_create_memory_invalid_memory_type(self, memory_service, sample_memory_data):
        """Test creation with invalid memory type."""
        # Setup
        sample_memory_data.memory_type = "invalid_type"

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.create_memory(sample_memory_data)

        assert "Invalid memory type" in exc_info.value.message
        mock_repository.create.assert_not_called()

    async def test_create_memory_invalid_confidence_low(self, memory_service, sample_memory_data):
        """Test creation with confidence below minimum."""
        # Setup
        sample_memory_data.confidence = CONFIDENCE_MIN - 0.1

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.create_memory(sample_memory_data)

        assert "Confidence must be between" in exc_info.value.message
        mock_repository.create.assert_not_called()

    async def test_create_memory_invalid_confidence_high(self, memory_service, sample_memory_data):
        """Test creation with confidence above maximum."""
        # Setup
        sample_memory_data.confidence = CONFIDENCE_MAX + 0.1

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.create_memory(sample_memory_data)

        assert "Confidence must be between" in exc_info.value.message
        mock_repository.create.assert_not_called()

    async def test_create_memory_empty_title(self, memory_service, sample_memory_data):
        """Test creation with empty title."""
        # Setup
        sample_memory_data.title = "   "

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.create_memory(sample_memory_data)

        assert "Title cannot be empty" in exc_info.value.message
        mock_repository.create.assert_not_called()

    async def test_create_memory_empty_content(self, memory_service, sample_memory_data):
        """Test creation with empty content."""
        # Setup
        sample_memory_data.content = ""

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.create_memory(sample_memory_data)

        assert "Content cannot be empty" in exc_info.value.message
        mock_repository.create.assert_not_called()

    async def test_create_memory_empty_scope(self, memory_service, sample_memory_data):
        """Test creation with empty scope."""
        # Setup
        sample_memory_data.scope = None

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.create_memory(sample_memory_data)

        assert "Scope is required" in exc_info.value.message
        mock_repository.create.assert_not_called()


class TestMemoryServiceGet:
    """Tests for get_memory method."""

    async def test_get_memory_success(self, memory_service, mock_repository):
        """Test successful memory retrieval."""
        # Setup
        memory_id = uuid4()
        expected_response = MemoryCardResponse(
            memory_id=memory_id,
            memory_type="episodic",
            title="Test Memory",
            content="Test content",
            confidence=0.8,
            scope="test_scope",
            source_events=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.get_by_id.return_value = expected_response

        # Execute
        result = await memory_service.get_memory(memory_id)

        # Verify
        assert result == expected_response
        mock_repository.get_by_id.assert_called_once_with(memory_id)

    async def test_get_memory_not_found(self, memory_service, mock_repository):
        """Test retrieval of non-existent memory."""
        # Setup
        memory_id = uuid4()
        mock_repository.get_by_id.return_value = None

        # Execute
        result = await memory_service.get_memory(memory_id)

        # Verify
        assert result is None
        mock_repository.get_by_id.assert_called_once_with(memory_id)


class TestMemoryServiceUpdate:
    """Tests for update_memory method."""

    async def test_update_memory_success(self, memory_service, mock_repository):
        """Test successful memory update."""
        # Setup
        memory_id = uuid4()
        update_data = MemoryCardUpdate(title="Updated Title")
        expected_response = MemoryCardResponse(
            memory_id=memory_id,
            memory_type="episodic",
            title="Updated Title",
            content="Test content",
            confidence=0.8,
            scope="test_scope",
            source_events=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.update.return_value = expected_response

        # Execute
        result = await memory_service.update_memory(memory_id, update_data)

        # Verify
        assert result == expected_response
        mock_repository.update.assert_called_once_with(memory_id, update_data)

    async def test_update_memory_invalid_confidence(self, memory_service, mock_repository):
        """Test update with invalid confidence."""
        # Setup
        memory_id = uuid4()
        update_data = MemoryCardUpdate(confidence=CONFIDENCE_MAX + 0.1)

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.update_memory(memory_id, update_data)

        assert "Confidence must be between" in exc_info.value.message
        mock_repository.update.assert_not_called()

    async def test_update_memory_empty_title(self, memory_service, mock_repository):
        """Test update with empty title."""
        # Setup
        memory_id = uuid4()
        update_data = MemoryCardUpdate(title="")

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.update_memory(memory_id, update_data)

        assert "Title cannot be empty" in exc_info.value.message
        mock_repository.update.assert_not_called()


class TestMemoryServiceList:
    """Tests for list_memories method."""

    async def test_list_memories_success(self, memory_service, mock_repository):
        """Test successful memory listing."""
        # Setup
        expected_memories = [
            MemoryCardResponse(
                memory_id=uuid4(),
                memory_type="episodic",
                title=f"Memory {i}",
                content=f"Content {i}",
                confidence=0.8,
                scope="test_scope",
                source_events=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            for i in range(3)
        ]
        mock_repository.list_memories.return_value = expected_memories

        # Execute
        result = await memory_service.list_memories()

        # Verify
        assert result == expected_memories
        mock_repository.list_memories.assert_called_once_with(
            memory_type=None,
            scope=None,
            min_confidence=None,
            limit=100,
            offset=0
        )

    async def test_list_memories_with_filters(self, memory_service, mock_repository):
        """Test memory listing with filters."""
        # Setup
        expected_memories = [MemoryCardResponse(
            memory_id=uuid4(),
            memory_type="semantic",
            title="Filtered Memory",
            content="Content",
            confidence=0.9,
            scope="filtered_scope",
            source_events=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )]
        mock_repository.list_memories.return_value = expected_memories

        # Execute
        result = await memory_service.list_memories(
            memory_type="semantic",
            scope="filtered_scope",
            min_confidence=0.8,
            limit=50,
            offset=10
        )

        # Verify
        assert result == expected_memories
        mock_repository.list_memories.assert_called_once_with(
            memory_type="semantic",
            scope="filtered_scope",
            min_confidence=0.8,
            limit=50,
            offset=10
        )

    async def test_list_memories_limit_too_high(self, memory_service, mock_repository):
        """Test list with limit exceeding maximum."""
        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.list_memories(limit=MAX_LIMIT + 1)

        assert "Limit cannot exceed" in exc_info.value.message
        mock_repository.list_memories.assert_not_called()

    async def test_list_memories_limit_too_low(self, memory_service, mock_repository):
        """Test list with limit below minimum."""
        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.list_memories(limit=MIN_LIMIT - 1)

        assert "Limit must be at least" in exc_info.value.message
        mock_repository.list_memories.assert_not_called()

    async def test_list_memories_offset_negative(self, memory_service, mock_repository):
        """Test list with negative offset."""
        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.list_memories(offset=-1)

        assert "Offset cannot be negative" in exc_info.value.message
        mock_repository.list_memories.assert_not_called()


class TestMemoryServiceSearch:
    """Tests for search_memories method."""

    async def test_search_memories_success(self, memory_service, mock_repository):
        """Test successful memory search."""
        # Setup
        query = "test query"
        expected_memories = [
            MemoryCardResponse(
                memory_id=uuid4(),
                memory_type="episodic",
                title="Matching Memory",
                content="Content with test query",
                confidence=0.8,
                scope="test_scope",
                source_events=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        mock_repository.search_memories.return_value = expected_memories

        # Execute
        result = await memory_service.search_memories(query)

        # Verify
        assert result == expected_memories
        mock_repository.search_memories.assert_called_once_with(
            query=query,
            memory_type=None,
            scope=None,
            limit=100
        )

    async def test_search_memories_empty_query(self, memory_service, mock_repository):
        """Test search with empty query."""
        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.search_memories("   ")

        assert "Search query cannot be empty" in exc_info.value.message
        mock_repository.search_memories.assert_not_called()

    async def test_search_memories_limit_exceeded(self, memory_service, mock_repository):
        """Test search with limit exceeding maximum."""
        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await memory_service.search_memories("test query", limit=MAX_LIMIT + 1)

        assert "Limit cannot exceed" in exc_info.value.message
        mock_repository.search_memories.assert_not_called()


class TestMemoryServiceCount:
    """Tests for count_memories method."""

    async def test_count_memories_success(self, memory_service, mock_repository):
        """Test successful memory count."""
        # Setup
        expected_count = 42
        mock_repository.count_memories.return_value = expected_count

        # Execute
        result = await memory_service.count_memories()

        # Verify
        assert result == expected_count
        mock_repository.count_memories.assert_called_once_with(
            memory_type=None,
            scope=None
        )

    async def test_count_memories_with_filters(self, memory_service, mock_repository):
        """Test memory count with filters."""
        # Setup
        expected_count = 10
        mock_repository.count_memories.return_value = expected_count

        # Execute
        result = await memory_service.count_memories(
            memory_type="episodic",
            scope="filtered_scope"
        )

        # Verify
        assert result == expected_count
        mock_repository.count_memories.assert_called_once_with(
            memory_type="episodic",
            scope="filtered_scope"
        )


class TestMemoryServiceStatistics:
    """Tests for get_memory_statistics method."""

    async def test_get_memory_statistics_success(self, memory_service, mock_repository):
        """Test successful statistics retrieval."""
        # Setup
        mock_repository.count_memories.side_effect = [100, 30, 40, 20, 10]

        # Execute
        result = await memory_service.get_memory_statistics()

        # Verify
        assert result["total_memories"] == 100
        assert result["by_memory_type"]["episodic"] == 30
        assert result["by_memory_type"]["semantic"] == 40
        assert result["scope"] == "all"

    async def test_get_memory_statistics_with_scope(self, memory_service, mock_repository):
        """Test statistics retrieval with scope filter."""
        # Setup
        mock_repository.count_memories.side_effect = [50, 15, 20, 10, 5]

        # Execute
        result = await memory_service.get_memory_statistics(scope="test_scope")

        # Verify
        assert result["total_memories"] == 50
        assert result["scope"] == "test_scope"
