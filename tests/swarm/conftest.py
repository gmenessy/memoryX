"""
Swarm Test Fixtures

Shared fixtures for swarm system tests.
"""
import pytest
from uuid import uuid4

from app.swarm.models.agent import AgentCreate, AgentType, AgentState
from app.swarm.models.prompt import PromptCreate, PromptType
from app.swarm.models.swarm import SwarmCreate, SwarmConfig
from app.swarm.models.task import TaskCreate, TaskPriority, TaskStatus


@pytest.fixture
def agent_factory():
    """Factory for creating test agents."""
    def _create(**kwargs):
        defaults = {
            "agent_type": AgentType.BASE,
            "name": f"test-agent-{uuid4().hex[:8]}",
            "capabilities": ["test"],
        }
        defaults.update(kwargs)
        return AgentCreate(**defaults)
    return _create


@pytest.fixture
def prompt_factory():
    """Factory for creating test prompts."""
    def _create(**kwargs):
        defaults = {
            "name": f"test-prompt-{uuid4().hex[:8]}",
            "prompt_type": PromptType.SYSTEM,
            "template": "You are a helpful assistant.",
            "version": "1.0.0",
        }
        defaults.update(kwargs)
        return PromptCreate(**defaults)
    return _create


@pytest.fixture
def swarm_factory():
    """Factory for creating test swarms."""
    def _create(**kwargs):
        defaults = {
            "name": f"test-swarm-{uuid4().hex[:8]}",
            "config": SwarmConfig(
                max_agents=10,
                coordination_type="hierarchical"
            ),
        }
        defaults.update(kwargs)
        return SwarmCreate(**defaults)
    return _create


@pytest.fixture
def task_factory():
    """Factory for creating test tasks."""
    def _create(**kwargs):
        defaults = {
            "title": f"test-task-{uuid4().hex[:8]}",
            "task_type": "process",
            "priority": TaskPriority.MEDIUM,
            "parameters": {},
        }
        defaults.update(kwargs)
        return TaskCreate(**defaults)
    return _create


@pytest.fixture
async def sample_agent(async_session, agent_factory):
    """Create a sample agent in database."""
    from app.swarm.services.agent_service import AgentService

    service = AgentService(async_session)
    return await service.create_agent(agent_factory())


@pytest.fixture
async def sample_prompt(async_session, prompt_factory):
    """Create a sample prompt in database."""
    from app.swarm.services.prompt_service import PromptService

    service = PromptService(async_session)
    return await service.create_prompt(prompt_factory())


@pytest.fixture
async def sample_swarm(async_session, swarm_factory):
    """Create a sample swarm in database."""
    from app.swarm.services.swarm_service import SwarmService

    service = SwarmService(async_session)
    return await service.create_swarm(swarm_factory())


@pytest.fixture
async def sample_task(async_session, sample_swarm, task_factory):
    """Create a sample task in database."""
    from app.swarm.services.task_service import TaskService

    service = TaskService(async_session)
    task_data = task_factory(swarm_id=sample_swarm.swarm_id)
    return await service.create_task(task_data)
