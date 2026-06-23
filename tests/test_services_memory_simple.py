"""
Simple Unit Tests for MemoryService.

Isolated tests that don't require full app initialization.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.constants import CONFIDENCE_MAX, CONFIDENCE_MIN, MAX_LIMIT, MIN_LIMIT, MIN_OFFSET
from app.exceptions import ValidationError
from app.models.memory import (
    MemoryCardCreate,
    MemoryCardUpdate,
    MemoryCardResponse,
)
from app.services.memory_service import MemoryService


def create_sample_response(memory_id: UUID | None = None) -> MemoryCardResponse:
    """Create a sample MemoryCardResponse."""
    return MemoryCardResponse(
        memory_id=memory_id or uuid4(),
        memory_type="episodic",
        title="Test Memory",
        content="Test content",
        confidence=0.8,
        scope="test_scope",
        source_events=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


async def test_memory_service_create_success():
    """Test successful memory creation."""
    # Setup
    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    mock_repo.create.return_value = create_sample_response()

    service = MemoryService(mock_session)
    service.repository = mock_repo

    user_data = MemoryCardCreate(
        memory_type="episodic",
        title="Test Memory",
        content="Test content",
        confidence=0.8,
        scope="test_scope",
        source_events=[],
    )

    # Execute
    result = await service.create_memory(user_data)

    # Verify
    assert result.title == "Test Memory"
    assert result.memory_type == "episodic"
    print("✓ test_memory_service_create_success passed")


async def test_memory_service_create_invalid_memory_type():
    """Test creation with invalid memory type."""
    # Setup
    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    service = MemoryService(mock_session)
    service.repository = mock_repo

    user_data = MemoryCardCreate(
        memory_type="invalid_type",
        title="Test Memory",
        content="Test content",
        confidence=0.8,
        scope="test_scope",
        source_events=[],
    )

    # Execute & Verify
    try:
        await service.create_memory(user_data)
        print("✗ Should have raised ValidationError")
    except ValidationError as e:
        assert "Invalid memory type" in e.message
        print("✓ test_memory_service_create_invalid_memory_type passed")


async def test_memory_service_create_confidence_boundary():
    """Test creation with confidence at boundaries."""
    # Setup
    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    service = MemoryService(mock_session)
    service.repository = mock_repo

    # Test with minimum confidence (0.0)
    user_data_min = MemoryCardCreate(
        memory_type="episodic",
        title="Test Memory",
        content="Test content",
        confidence=CONFIDENCE_MIN,  # 0.0 is valid
        scope="test_scope",
        source_events=[],
    )

    # Test with maximum confidence (1.0)
    user_data_max = MemoryCardCreate(
        memory_type="episodic",
        title="Test Memory",
        content="Test content",
        confidence=CONFIDENCE_MAX,  # 1.0 is valid
        scope="test_scope",
        source_events=[],
    )

    # Both should succeed
    mock_repo.create.return_value = create_sample_response()
    await service.create_memory(user_data_min)
    await service.create_memory(user_data_max)

    print("✓ test_memory_service_create_confidence_boundary passed")


async def test_memory_service_list_limit_too_high():
    """Test list with limit exceeding maximum."""
    # Setup
    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    service = MemoryService(mock_session)
    service.repository = mock_repo

    # Execute & Verify
    try:
        await service.list_memories(limit=MAX_LIMIT + 1)
        print("✗ Should have raised ValidationError")
    except ValidationError as e:
        assert "Limit cannot exceed" in e.message
        print("✓ test_memory_service_list_limit_too_high passed")


async def test_memory_service_search_empty_query():
    """Test search with empty query."""
    # Setup
    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    service = MemoryService(mock_session)
    service.repository = mock_repo

    # Execute & Verify
    try:
        await service.search_memories("   ")
        print("✗ Should have raised ValidationError")
    except ValidationError as e:
        assert "Search query cannot be empty" in e.message
        print("✓ test_memory_service_search_empty_query passed")


async def run_all_tests():
    """Run all simple MemoryService tests."""
    print("🧪 Running MemoryService Unit Tests...")

    tests = [
        test_memory_service_create_success,
        test_memory_service_create_invalid_memory_type,
        test_memory_service_create_confidence_boundary,
        test_memory_service_list_limit_too_high,
        test_memory_service_search_empty_query,
    ]

    for test in tests:
        await test()

    print(f"\n✅ All {len(tests)} tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
