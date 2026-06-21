"""
Tests for Memory Card System
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient

from app.main import app
from app.models.memory import MEMORY_TYPES
from app.database import get_db_session


@pytest.fixture(scope="function")
async def client():
    """Test client with database."""
    from tests.test_events import get_test_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        app.dependency_overrides[get_db_session] = get_test_db
        yield ac
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_memory(client):
    """Test creating a new memory card."""
    memory_data = {
        "memory_type": "semantic",
        "title": "Python Programming",
        "content": "Python is a high-level programming language known for its simplicity.",
        "confidence": 0.9,
        "scope": "global",
        "source_events": []
    }

    response = await client.post("/api/memory/", json=memory_data)

    assert response.status_code == 201
    data = response.json()

    assert data["memory_type"] == "semantic"
    assert data["title"] == "Python Programming"
    assert data["content"] == "Python is a high-level programming language known for its simplicity."
    assert data["confidence"] == 0.9
    assert data["scope"] == "global"
    assert "memory_id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_memory_invalid_type(client):
    """Test creating memory with invalid type."""
    memory_data = {
        "memory_type": "invalid_type",
        "title": "Test",
        "content": "Test content",
        "confidence": 0.5,
        "scope": "global"
    }

    response = await client.post("/api/memory/", json=memory_data)

    assert response.status_code == 400
    assert "Invalid memory type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_memory_invalid_confidence(client):
    """Test creating memory with invalid confidence."""
    memory_data = {
        "memory_type": "semantic",
        "title": "Test",
        "content": "Test content",
        "confidence": 1.5,  # Invalid: > 1.0
        "scope": "global"
    }

    response = await client.post("/api/memory/", json=memory_data)

    # This should be caught by Pydantic validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_memory_empty_title(client):
    """Test creating memory with empty title."""
    memory_data = {
        "memory_type": "semantic",
        "title": "   ",  # Empty after strip
        "content": "Test content",
        "confidence": 0.5,
        "scope": "global"
    }

    response = await client.post("/api/memory/", json=memory_data)

    assert response.status_code == 400
    assert "Title cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_memory_with_source_events(client):
    """Test creating memory with source events."""
    # First create an event
    event_data = {
        "event_type": "user_input",
        "actor": "user_123",
        "scope": "session_1",
        "payload": {"message": "Tell me about Python"}
    }

    event_response = await client.post("/api/events/", json=event_data)
    event_id = event_response.json()["event_id"]

    # Now create memory with source event
    memory_data = {
        "memory_type": "semantic",
        "title": "Python Knowledge",
        "content": "Python is a programming language",
        "confidence": 0.8,
        "scope": "session_1",
        "source_events": [event_id]
    }

    response = await client.post("/api/memory/", json=memory_data)

    assert response.status_code == 201
    data = response.json()
    assert len(data["source_events"]) == 1
    assert data["source_events"][0] == event_id


@pytest.mark.asyncio
async def test_list_memories_empty(client):
    """Test listing memories when none exist."""
    response = await client.get("/api/memory/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_memories_with_data(client):
    """Test listing memories after creating some."""
    memories = [
        {
            "memory_type": "episodic",
            "title": f"Memory {i}",
            "content": f"Content {i}",
            "confidence": 0.7,
            "scope": "session_1"
        }
        for i in range(3)
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    response = await client.get("/api/memory/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_memory_by_id(client):
    """Test getting a specific memory by ID."""
    memory_data = {
        "memory_type": "procedural",
        "title": "How to bake a cake",
        "content": "Mix ingredients and bake at 180°C",
        "confidence": 0.85,
        "scope": "global"
    }

    create_response = await client.post("/api/memory/", json=memory_data)
    memory_id = create_response.json()["memory_id"]

    response = await client.get(f"/api/memory/{memory_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["memory_id"] == memory_id
    assert data["title"] == "How to bake a cake"


@pytest.mark.asyncio
async def test_get_nonexistent_memory(client):
    """Test getting a memory that doesn't exist."""
    fake_id = uuid4()
    response = await client.get(f"/api/memory/{fake_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_memory(client):
    """Test updating a memory card."""
    # Create memory
    memory_data = {
        "memory_type": "semantic",
        "title": "Original Title",
        "content": "Original content",
        "confidence": 0.7,
        "scope": "global"
    }

    create_response = await client.post("/api/memory/", json=memory_data)
    memory_id = create_response.json()["memory_id"]
    original_updated_at = create_response.json()["updated_at"]

    # Update memory
    update_data = {
        "title": "Updated Title",
        "confidence": 0.9
    }

    response = await client.put(f"/api/memory/{memory_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["confidence"] == 0.9
    assert data["content"] == "Original content"  # Unchanged
    assert data["updated_at"] != original_updated_at  # Timestamp updated


@pytest.mark.asyncio
async def test_search_memories(client):
    """Test searching memories by query."""
    # Create memories
    memories = [
        {
            "memory_type": "semantic",
            "title": "Python Programming",
            "content": "Python is a programming language",
            "confidence": 0.9,
            "scope": "global"
        },
        {
            "memory_type": "semantic",
            "title": "Java Programming",
            "content": "Java is another programming language",
            "confidence": 0.8,
            "scope": "global"
        },
        {
            "memory_type": "episodic",
            "title": "My Vacation",
            "content": "I went to the beach last summer",
            "confidence": 0.7,
            "scope": "personal"
        }
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    # Search for "programming"
    response = await client.get("/api/memory/search?query=programming")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("programming" in m["title"].lower() or "programming" in m["content"].lower() for m in data)


@pytest.mark.asyncio
async def test_filter_memories_by_type(client):
    """Test filtering memories by type."""
    memories = [
        {
            "memory_type": "semantic",
            "title": "Fact 1",
            "content": "Semantic content",
            "confidence": 0.8,
            "scope": "global"
        },
        {
            "memory_type": "episodic",
            "title": "Event 1",
            "content": "Episodic content",
            "confidence": 0.7,
            "scope": "global"
        },
        {
            "memory_type": "semantic",
            "title": "Fact 2",
            "content": "More semantic content",
            "confidence": 0.9,
            "scope": "global"
        }
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    # Filter by semantic type
    response = await client.get("/api/memory/?memory_type=semantic")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(m["memory_type"] == "semantic" for m in data)


@pytest.mark.asyncio
async def test_filter_memories_by_confidence(client):
    """Test filtering memories by minimum confidence."""
    memories = [
        {
            "memory_type": "semantic",
            "title": "High confidence",
            "content": "Content",
            "confidence": 0.9,
            "scope": "global"
        },
        {
            "memory_type": "semantic",
            "title": "Low confidence",
            "content": "Content",
            "confidence": 0.3,
            "scope": "global"
        }
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    # Filter by min confidence
    response = await client.get("/api/memory/?min_confidence=0.7")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["confidence"] >= 0.7


@pytest.mark.asyncio
async def test_list_memory_types(client):
    """Test getting available memory types."""
    response = await client.get("/api/memory/types")

    assert response.status_code == 200
    types = response.json()
    assert isinstance(types, list)
    assert "semantic" in types
    assert "episodic" in types
    assert "procedural" in types


@pytest.mark.asyncio
async def test_memory_statistics(client):
    """Test getting memory statistics."""
    memories = [
        {
            "memory_type": "semantic",
            "title": "Fact 1",
            "content": "Content",
            "confidence": 0.8,
            "scope": "session_1"
        },
        {
            "memory_type": "episodic",
            "title": "Event 1",
            "content": "Content",
            "confidence": 0.7,
            "scope": "session_1"
        },
        {
            "memory_type": "semantic",
            "title": "Fact 2",
            "content": "Content",
            "confidence": 0.9,
            "scope": "session_2"
        }
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    # Get global statistics
    response = await client.get("/api/memory/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_memories"] == 3
    assert data["by_memory_type"]["semantic"] == 2
    assert data["by_memory_type"]["episodic"] == 1

    # Get scoped statistics
    response = await client.get("/api/memory/statistics?scope=session_1")
    assert response.status_code == 200
    data = response.json()
    assert data["total_memories"] == 2
    assert data["scope"] == "session_1"


@pytest.mark.asyncio
async def test_count_memories(client):
    """Test counting memories."""
    memories = [
        {
            "memory_type": "semantic",
            "title": "Fact 1",
            "content": "Content",
            "confidence": 0.8,
            "scope": "global"
        },
        {
            "memory_type": "semantic",
            "title": "Fact 2",
            "content": "Content",
            "confidence": 0.7,
            "scope": "global"
        }
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    # Count all memories
    response = await client.get("/api/memory/count")
    assert response.status_code == 200
    assert response.json()["count"] == 2

    # Count by type
    response = await client.get("/api/memory/count?memory_type=semantic")
    assert response.status_code == 200
    assert response.json()["count"] == 2

    # Count by different type
    response = await client.get("/api/memory/count?memory_type=episodic")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.asyncio
async def test_get_memories_by_event(client):
    """Test getting memories derived from a specific event."""
    # Create an event
    event_data = {
        "event_type": "user_input",
        "actor": "user_123",
        "scope": "session_1",
        "payload": {"message": "Tell me about AI"}
    }

    event_response = await client.post("/api/events/", json=event_data)
    event_id = event_response.json()["event_id"]

    # Create memories from this event
    memories = [
        {
            "memory_type": "semantic",
            "title": "AI Knowledge 1",
            "content": "AI is a field of computer science",
            "confidence": 0.9,
            "scope": "session_1",
            "source_events": [event_id]
        },
        {
            "memory_type": "semantic",
            "title": "AI Knowledge 2",
            "content": "Machine Learning is a subset of AI",
            "confidence": 0.8,
            "scope": "session_1",
            "source_events": [event_id]
        }
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    # Get memories by event
    response = await client.get(f"/api/memory/event/{event_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(event_id in m["source_events"] for m in data)


@pytest.mark.asyncio
async def test_pagination(client):
    """Test memory pagination."""
    memories = [
        {
            "memory_type": "semantic",
            "title": f"Memory {i}",
            "content": f"Content {i}",
            "confidence": 0.7,
            "scope": "global"
        }
        for i in range(15)
    ]

    for memory in memories:
        await client.post("/api/memory/", json=memory)

    # Get first page
    response = await client.get("/api/memory/?limit=10&offset=0")
    assert response.status_code == 200
    first_page = response.json()
    assert len(first_page) == 10

    # Get second page
    response = await client.get("/api/memory/?limit=10&offset=10")
    assert response.status_code == 200
    second_page = response.json()
    assert len(second_page) == 5


@pytest.mark.asyncio
async def test_pagination_limits(client):
    """Test pagination limits are enforced."""
    # Test limit too high
    response = await client.get("/api/memory/?limit=1001")
    assert response.status_code == 400

    # Test limit too low
    response = await client.get("/api/memory/?limit=0")
    assert response.status_code == 400

    # Test negative offset
    response = await client.get("/api/memory/?offset=-1")
    assert response.status_code == 400