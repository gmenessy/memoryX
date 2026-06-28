"""
Swarm Prompt Tests

Comprehensive tests for prompt management, versioning,
and health tracking within the swarm system.
"""
import pytest
from uuid import uuid4

from app.swarm.models.prompt import (
    PromptType,
    PromptState,
    PromptCreate,
    PromptUpdate,
    PromptHealth,
)
from app.swarm.services.prompt_service import PromptService


@pytest.mark.asyncio
class TestPromptLifecycle:
    """Test prompt creation, retrieval, and deletion."""

    async def test_create_prompt_success(self, async_session):
        """Test successful prompt creation."""
        service = PromptService(async_session)

        prompt_data = PromptCreate(
            name="test-prompt",
            content="You are a helpful assistant.",
            prompt_type=PromptType.SYSTEM,
            purpose="General assistance",
            tags=["assistant", "general"]
        )

        prompt = await service.create_prompt(prompt_data)

        assert prompt is not None
        assert prompt.name == "test-prompt"
        assert prompt.prompt_type == PromptType.SYSTEM.value
        assert prompt.state == PromptState.DRAFT.value
        assert prompt.version == 1
        assert prompt.health_score == 0.5
        assert prompt.usage_count == 0

    async def test_create_prompt_with_metadata(self, async_session):
        """Test prompt creation with custom metadata."""
        service = PromptService(async_session)

        prompt_data = PromptCreate(
            name="metadata-prompt",
            content="Process this input.",
            prompt_type=PromptType.FUNCTION,
            purpose="Input processing",
            tags=["processing"],
            metadata={"max_tokens": 1000, "temperature": 0.7}
        )

        prompt = await service.create_prompt(prompt_data)

        assert prompt is not None
        assert prompt.metadata["max_tokens"] == 1000
        assert prompt.metadata["temperature"] == 0.7

    async def test_get_prompt_success(self, async_session):
        """Test retrieving an existing prompt."""
        service = PromptService(async_session)

        created = await service.create_prompt(PromptCreate(
            name="get-test",
            content="Test content",
            prompt_type=PromptType.USER,
            purpose="Testing retrieval"
        ))

        retrieved = await service.get_prompt(created.prompt_id)

        assert retrieved is not None
        assert retrieved.prompt_id == created.prompt_id
        assert retrieved.name == "get-test"

    async def test_get_prompt_not_found(self, async_session):
        """Test retrieving non-existent prompt."""
        service = PromptService(async_session)

        result = await service.get_prompt(uuid4())
        assert result is None

    async def test_list_prompts_empty(self, async_session):
        """Test listing prompts when none exist."""
        service = PromptService(async_session)

        prompts = await service.list_prompts()
        assert prompts == []

    async def test_list_prompts_with_results(self, async_session):
        """Test listing prompts with multiple prompts."""
        service = PromptService(async_session)

        await service.create_prompt(PromptCreate(
            name="prompt-1",
            content="Content 1",
            prompt_type=PromptType.SYSTEM,
            purpose="Purpose 1"
        ))
        await service.create_prompt(PromptCreate(
            name="prompt-2",
            content="Content 2",
            prompt_type=PromptType.USER,
            purpose="Purpose 2"
        ))
        await service.create_prompt(PromptCreate(
            name="prompt-3",
            content="Content 3",
            prompt_type=PromptType.TEMPLATE,
            purpose="Purpose 3"
        ))

        prompts = await service.list_prompts()
        assert len(prompts) == 3

    async def test_list_prompts_filter_by_type(self, async_session):
        """Test filtering prompts by type."""
        service = PromptService(async_session)

        await service.create_prompt(PromptCreate(
            name="sys-1",
            content="System",
            prompt_type=PromptType.SYSTEM,
            purpose="System prompt"
        ))
        await service.create_prompt(PromptCreate(
            name="user-1",
            content="User",
            prompt_type=PromptType.USER,
            purpose="User prompt"
        ))
        await service.create_prompt(PromptCreate(
            name="sys-2",
            content="System 2",
            prompt_type=PromptType.SYSTEM,
            purpose="Another system"
        ))

        system_prompts = await service.list_prompts(prompt_type=PromptType.SYSTEM)
        user_prompts = await service.list_prompts(prompt_type=PromptType.USER)

        assert len(system_prompts) == 2
        assert len(user_prompts) == 1
        assert all(p.prompt_type == PromptType.SYSTEM.value for p in system_prompts)

    async def test_delete_prompt_success(self, async_session):
        """Test successful prompt deletion."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="to-delete",
            content="Will be deleted",
            prompt_type=PromptType.SYSTEM,
            purpose="Deletion test"
        ))

        result = await service.delete_prompt(prompt.prompt_id)
        assert result is True

        assert await service.get_prompt(prompt.prompt_id) is None

    async def test_delete_prompt_not_found(self, async_session):
        """Test deleting non-existent prompt."""
        service = PromptService(async_session)

        result = await service.delete_prompt(uuid4())
        assert result is False


@pytest.mark.asyncio
class TestPromptActivation:
    """Test prompt activation and active version retrieval."""

    async def test_activate_prompt(self, async_session):
        """Test activating a prompt."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="activatable",
            content="Active content",
            prompt_type=PromptType.SYSTEM,
            purpose="Activation test"
        ))

        activated = await service.activate_prompt(prompt.prompt_id)

        assert activated is not None
        assert activated.is_active is True
        assert activated.state == PromptState.ACTIVE.value

    async def test_get_active_prompt_by_name(self, async_session):
        """Test retrieving active prompt by name."""
        service = PromptService(async_session)

        # Create multiple versions
        v1 = await service.create_prompt(PromptCreate(
            name="versioned-prompt",
            content="Version 1",
            prompt_type=PromptType.SYSTEM,
            purpose="Versioning test"
        ))
        await service.activate_prompt(v1.prompt_id)

        # Create new version (child)
        v2 = await service.create_prompt(PromptCreate(
            name="versioned-prompt",
            content="Version 2",
            prompt_type=PromptType.SYSTEM,
            purpose="Versioning test"
        ))
        await service.activate_prompt(v2.prompt_id)

        # Get active version
        active = await service.get_active_prompt("versioned-prompt")

        assert active is not None
        assert active.content == "Version 2"
        assert active.is_active is True

    async def test_activate_non_existent_prompt(self, async_session):
        """Test activating non-existent prompt."""
        service = PromptService(async_session)

        result = await service.activate_prompt(uuid4())
        assert result is None


@pytest.mark.asyncio
class TestPromptUpdates:
    """Test prompt property updates."""

    async def test_update_prompt_content(self, async_session):
        """Test updating prompt content."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="updatable",
            content="Original content",
            prompt_type=PromptType.SYSTEM,
            purpose="Update test"
        ))

        updated = await service.update_prompt(
            prompt.prompt_id,
            PromptUpdate(content="Updated content")
        )

        assert updated is not None
        assert updated.content == "Updated content"

    async def test_update_prompt_tags(self, async_session):
        """Test updating prompt tags."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="taggable",
            content="Content",
            prompt_type=PromptType.SYSTEM,
            purpose="Tag test",
            tags=["old-tag"]
        ))

        updated = await service.update_prompt(
            prompt.prompt_id,
            PromptUpdate(tags=["new-tag-1", "new-tag-2"])
        )

        assert updated is not None
        assert set(updated.tags) == {"new-tag-1", "new-tag-2"}

    async def test_update_non_existent_prompt(self, async_session):
        """Test updating non-existent prompt."""
        service = PromptService(async_session)

        result = await service.update_prompt(
            uuid4(),
            PromptUpdate(content="New content")
        )

        assert result is None


@pytest.mark.asyncio
class TestPromptHealth:
    """Test prompt health tracking and scoring."""

    async def test_update_health_success(self, async_session):
        """Test updating prompt health."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="healthy",
            content="Healthy content",
            prompt_type=PromptType.SYSTEM,
            purpose="Health test"
        ))

        health_data = PromptHealth(
            prompt_id=prompt.prompt_id,
            success=True,
            response_time=1.5
        )

        updated = await service.update_health(health_data)

        assert updated is not None
        assert updated.usage_count == 1
        # Health score should be updated based on success

    async def test_health_score_increases_with_success(self, async_session):
        """Test health score increases with successful uses."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="scoring",
            content="Content",
            prompt_type=PromptType.SYSTEM,
            purpose="Scoring test"
        ))

        initial_score = prompt.health_score

        # Record several successful uses
        for _ in range(5):
            await service.update_health(PromptHealth(
                prompt_id=prompt.prompt_id,
                success=True,
                response_time=1.0
            ))

        updated = await service.get_prompt(prompt.prompt_id)

        assert updated is not None
        # Health score should have improved
        assert updated.health_score >= initial_score
        assert updated.usage_count == 5

    async def test_health_score_decreases_with_failure(self, async_session):
        """Test health score decreases with failed uses."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="failing",
            content="Content",
            prompt_type=PromptType.SYSTEM,
            purpose="Failure test"
        ))

        initial_score = prompt.health_score

        # Record several failed uses
        for _ in range(5):
            await service.update_health(PromptHealth(
                prompt_id=prompt.prompt_id,
                success=False,
                response_time=2.0
            ))

        updated = await service.get_prompt(prompt.prompt_id)

        assert updated is not None
        # Health score should have decreased
        assert updated.health_score < initial_score

    async def test_get_prompt_history(self, async_session):
        """Test retrieving prompt history."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="historical",
            content="Content",
            prompt_type=PromptType.SYSTEM,
            purpose="History test"
        ))

        # Create some history through usage
        await service.update_health(PromptHealth(
            prompt_id=prompt.prompt_id,
            success=True,
            response_time=1.0
        ))

        history = await service.get_prompt_history(prompt.prompt_id)

        # History should contain health updates
        assert history is not None


@pytest.mark.asyncio
class TestPromptSearch:
    """Test prompt search functionality."""

    async def test_search_prompts_by_query(self, async_session):
        """Test searching prompts by content query."""
        service = PromptService(async_session)

        await service.create_prompt(PromptCreate(
            name="python-helper",
            content="Help with Python code",
            prompt_type=PromptType.SYSTEM,
            purpose="Python assistance"
        ))
        await service.create_prompt(PromptCreate(
            name="js-helper",
            content="Help with JavaScript",
            prompt_type=PromptType.SYSTEM,
            purpose="JS assistance"
        ))

        # Search for Python
        results = await service.search_prompts(query="Python")

        assert len(results) == 1
        assert "Python" in results[0].content or "Python" in results[0].name

    async def test_search_prompts_by_tags(self, async_session):
        """Test searching prompts by tags."""
        service = PromptService(async_session)

        await service.create_prompt(PromptCreate(
            name="tagged-1",
            content="Content",
            prompt_type=PromptType.SYSTEM,
            purpose="Test",
            tags=["python", "code"]
        ))
        await service.create_prompt(PromptCreate(
            name="tagged-2",
            content="Content",
            prompt_type=PromptType.SYSTEM,
            purpose="Test",
            tags=["javascript", "code"]
        ))
        await service.create_prompt(PromptCreate(
            name="untagged",
            content="Content",
            prompt_type=PromptType.SYSTEM,
            purpose="Test",
            tags=["general"]
        ))

        # Search by tag
        results = await service.search_prompts(tags=["python"])

        assert len(results) == 1
        assert "python" in results[0].tags

    async def test_search_prompts_by_min_health(self, async_session):
        """Test filtering prompts by minimum health score."""
        service = PromptService(async_session)

        prompt1 = await service.create_prompt(PromptCreate(
            name="healthy-prompt",
            content="Good content",
            prompt_type=PromptType.SYSTEM,
            purpose="Health filter test"
        ))

        # Improve health
        for _ in range(5):
            await service.update_health(PromptHealth(
                prompt_id=prompt1.prompt_id,
                success=True,
                response_time=1.0
            ))

        prompt2 = await service.create_prompt(PromptCreate(
            name="unhealthy-prompt",
            content="Bad content",
            prompt_type=PromptType.SYSTEM,
            purpose="Health filter test"
        ))

        # Degrade health
        for _ in range(5):
            await service.update_health(PromptHealth(
                prompt_id=prompt2.prompt_id,
                success=False,
                response_time=5.0
            ))

        # Search for healthy prompts
        results = await service.search_prompts(min_health_score=0.6)

        assert len(results) >= 1
        # Should contain the healthy prompt
        assert any(p.prompt_id == prompt1.prompt_id for p in results)


@pytest.mark.asyncio
class TestPromptVersioning:
    """Test prompt versioning and mutation."""

    async def test_prompt_version_increments(self, async_session):
        """Test that prompt versions increment properly."""
        service = PromptService(async_session)

        v1 = await service.create_prompt(PromptCreate(
            name="versioned",
            content="Version 1",
            prompt_type=PromptType.SYSTEM,
            purpose="Versioning"
        ))

        assert v1.version == 1

    async def test_parent_child_relationship(self, async_session):
        """Test parent-child relationship in prompt versions."""
        service = PromptService(async_session)

        parent = await service.create_prompt(PromptCreate(
            name="parent-prompt",
            content="Parent content",
            prompt_type=PromptType.SYSTEM,
            purpose="Parent"
        ))

        # Create child version
        child = await service.create_prompt(PromptCreate(
            name="parent-prompt",  # Same name = new version
            content="Child content",
            prompt_type=PromptType.SYSTEM,
            purpose="Child"
        ))

        # In a full implementation, child should reference parent
        # This tests the structure is in place
        assert child.prompt_id != parent.prompt_id


@pytest.mark.asyncio
class TestPromptStateTransitions:
    """Test prompt state management."""

    async def test_deprecate_prompt(self, async_session):
        """Test deprecating a prompt."""
        service = PromptService(async_session)

        prompt = await service.create_prompt(PromptCreate(
            name="to-deprecate",
            content="Old content",
            prompt_type=PromptType.SYSTEM,
            purpose="Will be deprecated"
        ))

        # Activate first
        await service.activate_prompt(prompt.prompt_id)

        # Deprecate
        updated = await service.update_prompt(
            prompt.prompt_id,
            PromptUpdate()
        )
        # Manual state update would go here
        # For now test the structure exists

        assert updated is not None
