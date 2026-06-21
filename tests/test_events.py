"""
Tests for Event System
"""
import pytest
from uuid import uuid4
from datetime import datetime
from httpx import AsyncClient

from app.main import app
from app.models.event import EventCreate, EVENT_TYPES
from app.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.models.event import EventDB


class Base(DeclarativeBase):
    pass


# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, future=True)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_test_db():
    """Test database session."""
    async with async_session_factory() as session:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(scope="function")
async def client():
    """Test client with database."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        app.dependency_overrides[get_db_session] = get_test_db
        yield ac
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_event(client):
    """Test creating a new event."""
    event_data = {
        "event_type": "user_input",
        "actor": "user_123",
        "scope": "session_456",
        "payload": {"message": "Hello, world!"},
        "metadata": {"source": "web"}
    }

    response = await client.post("/api/events/", json=event_data)

    assert response.status_code == 201
    data = response.json()

    assert data["event_type"] == "user_input"
    assert data["actor"] == "user_123"
    assert data["scope"] == "session_456"
    assert data["payload"]["message"] == "Hello, world!"
    assert "event_id" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_create_event_invalid_type(client):
    """Test creating event with invalid type."""
    event_data = {
        "event_type": "invalid_type",
        "actor": "user_123",
        "scope": "session_456",
        "payload": {}
    }

    response = await client.post("/api/events/", json=event_data)

    assert response.status_code == 400
    assert "Invalid event type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_event_missing_fields(client):
    """Test creating event with missing required fields."""
    event_data = {
        "event_type": "user_input",
        # Missing actor and scope
    }

    response = await client.post("/api/events/", json=event_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_events_empty(client):
    """Test listing events when none exist."""
    response = await client.get("/api/events/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_events_with_data(client):
    """Test listing events after creating some."""
    # Create multiple events
    events = [
        {
            "event_type": "user_input",
            "actor": "user_123",
            "scope": "session_456",
            "payload": {"message": f"Message {i}"}
        }
        for i in range(3)
    ]

    for event in events:
        await client.post("/api/events/", json=event)

    # List events
    response = await client.get("/api/events/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_event_by_id(client):
    """Test getting a specific event by ID."""
    # Create an event
    event_data = {
        "event_type": "agent_action",
        "actor": "agent_789",
        "scope": "case_101",
        "payload": {"action": "search"}
    }

    create_response = await client.post("/api/events/", json=event_data)
    event_id = create_response.json()["event_id"]

    # Get the event
    response = await client.get(f"/api/events/{event_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == event_id
    assert data["event_type"] == "agent_action"


@pytest.mark.asyncio
async def test_get_nonexistent_event(client):
    """Test getting an event that doesn't exist."""
    fake_id = uuid4()
    response = await client.get(f"/api/events/{fake_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_event_types(client):
    """Test getting available event types."""
    response = await client.get("/api/events/types")

    assert response.status_code == 200
    types = response.json()
    assert isinstance(types, list)
    assert "user_input" in types
    assert "agent_action" in types
    assert "tool_call" in types


@pytest.mark.asyncio
async def test_event_statistics(client):
    """Test getting event statistics."""
    # Create events of different types
    events = [
        {"event_type": "user_input", "actor": "user_123", "scope": "session_1"},
        {"event_type": "agent_action", "actor": "agent_456", "scope": "session_1"},
        {"event_type": "user_input", "actor": "user_789", "scope": "session_2"},
    ]

    for event in events:
        await client.post("/api/events/", json=event)

    # Get statistics
    response = await client.get("/api/events/statistics")

    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "by_event_type" in data
    assert data["total_events"] == 3


@pytest.mark.asyncio
async def test_count_events(client):
    """Test counting events."""
    # Create some events
    events = [
        {"event_type": "user_input", "actor": "user_123", "scope": "session_1"},
        {"event_type": "user_input", "actor": "user_456", "scope": "session_2"},
    ]

    for event in events:
        await client.post("/api/events/", json=event)

    # Count all events
    response = await client.get("/api/events/count")
    assert response.status_code == 200
    assert response.json()["count"] == 2

    # Count by type
    response = await client.get("/api/events/count?event_type=user_input")
    assert response.status_code == 200
    assert response.json()["count"] == 2

    # Count by different type
    response = await client.get("/api/events/count?event_type=agent_action")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.asyncio
async def test_filter_events_by_type(client):
    """Test filtering events by type."""
    # Create events of different types
    events = [
        {"event_type": "user_input", "actor": "user_123", "scope": "session_1"},
        {"event_type": "agent_action", "actor": "agent_456", "scope": "session_1"},
        {"event_type": "user_input", "actor": "user_789", "scope": "session_2"},
    ]

    for event in events:
        await client.post("/api/events/", json=event)

    # Filter by user_input type
    response = await client.get("/api/events/?event_type=user_input")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(e["event_type"] == "user_input" for e in data)


@pytest.mark.asyncio
async def test_filter_events_by_scope(client):
    """Test filtering events by scope."""
    # Create events with different scopes
    events = [
        {"event_type": "user_input", "actor": "user_123", "scope": "session_1"},
        {"event_type": "agent_action", "actor": "agent_456", "scope": "session_1"},
        {"event_type": "user_input", "actor": "user_789", "scope": "session_2"},
    ]

    for event in events:
        await client.post("/api/events/", json=event)

    # Filter by scope
    response = await client.get("/api/events/?scope=session_1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(e["scope"] == "session_1" for e in data)


@pytest.mark.asyncio
async def test_pagination(client):
    """Test event pagination."""
    # Create many events
    events = [
        {"event_type": "user_input", "actor": f"user_{i}", "scope": "session_1"}
        for i in range(15)
    ]

    for event in events:
        await client.post("/api/events/", json=event)

    # Get first page
    response = await client.get("/api/events/?limit=10&offset=0")
    assert response.status_code == 200
    first_page = response.json()
    assert len(first_page) == 10

    # Get second page
    response = await client.get("/api/events/?limit=10&offset=10")
    assert response.status_code == 200
    second_page = response.json()
    assert len(second_page) == 5


@pytest.mark.asyncio
async def test_pagination_limits(client):
    """Test pagination limits are enforced."""
    # Test limit too high
    response = await client.get("/api/events/?limit=1001")
    assert response.status_code == 400

    # Test limit too low
    response = await client.get("/api/events/?limit=0")
    assert response.status_code == 400

    # Test negative offset
    response = await client.get("/api/events/?offset=-1")
    assert response.status_code == 400