"""
Swarm Agent Tests

Comprehensive tests for agent lifecycle, state management,
and operations within the swarm system.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.swarm.models.agent import (
    AgentType,
    AgentState,
    AgentCreate,
    AgentUpdate,
    AgentHeartbeat,
    AgentConfig,
)
from app.swarm.services.agent_service import AgentService
from app.swarm.repositories.agent_repository import AgentRepository


@pytest.mark.asyncio
class TestAgentLifecycle:
    """Test agent creation, retrieval, and deletion."""

    async def test_create_agent_success(self, async_session):
        """Test successful agent creation."""
        service = AgentService(async_session)

        agent_data = AgentCreate(
            agent_type=AgentType.BASE,
            name="test-agent",
            capabilities=["read", "write"],
            config=AgentConfig(max_concurrent_tasks=2)
        )

        agent = await service.create_agent(agent_data)

        assert agent is not None
        assert agent.name == "test-agent"
        assert agent.agent_type == AgentType.BASE.value
        assert agent.state == AgentState.IDLE.value
        assert agent.capabilities == ["read", "write"]
        assert agent.current_task_id is None
        assert agent.agent_id is not None

    async def test_create_agent_invalid_name(self, async_session):
        """Test agent creation fails with invalid name."""
        service = AgentService(async_session)

        with pytest.raises(ValueError, match="Agent name is required"):
            await service.create_agent(AgentCreate(
                agent_type=AgentType.BASE,
                name="",  # Empty name
                capabilities=[]
            ))

        with pytest.raises(ValueError, match="Agent name is required"):
            await service.create_agent(AgentCreate(
                agent_type=AgentType.BASE,
                name="   ",  # Whitespace only
                capabilities=[]
            ))

    async def test_create_agent_invalid_capabilities(self, async_session):
        """Test agent creation fails with invalid capabilities."""
        service = AgentService(async_session)

        with pytest.raises(ValueError, match="Capabilities must be a list"):
            await service.create_agent(AgentCreate(
                agent_type=AgentType.BASE,
                name="test-agent",
                capabilities="not-a-list"  # Wrong type
            ))

    async def test_get_agent_success(self, async_session):
        """Test retrieving an existing agent."""
        service = AgentService(async_session)

        # Create an agent first
        created = await service.create_agent(AgentCreate(
            agent_type=AgentType.RESEARCH,
            name="research-agent-1",
            capabilities=["search", "analyze"]
        ))

        # Retrieve the agent
        retrieved = await service.get_agent(created.agent_id)

        assert retrieved is not None
        assert retrieved.agent_id == created.agent_id
        assert retrieved.name == "research-agent-1"

    async def test_get_agent_not_found(self, async_session):
        """Test retrieving a non-existent agent."""
        service = AgentService(async_session)

        result = await service.get_agent(uuid4())
        assert result is None

    async def test_list_agents_empty(self, async_session):
        """Test listing agents when none exist."""
        service = AgentService(async_session)

        agents = await service.list_agents()
        assert agents == []

    async def test_list_agents_with_results(self, async_session):
        """Test listing agents with multiple agents."""
        service = AgentService(async_session)

        # Create multiple agents
        await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="agent-1",
            capabilities=["task1"]
        ))
        await service.create_agent(AgentCreate(
            agent_type=AgentType.EVAL,
            name="agent-2",
            capabilities=["task2"]
        ))
        await service.create_agent(AgentCreate(
            agent_type=AgentType.RESEARCH,
            name="agent-3",
            capabilities=["task3"]
        ))

        agents = await service.list_agents()
        assert len(agents) == 3

    async def test_list_agents_filter_by_type(self, async_session):
        """Test filtering agents by type."""
        service = AgentService(async_session)

        # Create agents of different types
        await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="base-agent",
            capabilities=[]
        ))
        await service.create_agent(AgentCreate(
            agent_type=AgentType.EVAL,
            name="eval-agent",
            capabilities=[]
        ))
        await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="base-agent-2",
            capabilities=[]
        ))

        base_agents = await service.list_agents(agent_type=AgentType.BASE)
        eval_agents = await service.list_agents(agent_type=AgentType.EVAL)

        assert len(base_agents) == 2
        assert len(eval_agents) == 1
        assert all(a.agent_type == AgentType.BASE.value for a in base_agents)

    async def test_list_agents_filter_by_state(self, async_session):
        """Test filtering agents by state."""
        service = AgentService(async_session)

        # Create and start agents
        agent1 = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="idle-agent",
            capabilities=[]
        ))
        agent2 = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="active-agent",
            capabilities=[]
        ))

        # Start one agent
        await service.start_agent(agent2.agent_id)

        idle_agents = await service.list_agents(state=AgentState.IDLE)
        active_agents = await service.list_agents(state=AgentState.ACTIVE)

        assert len(idle_agents) == 1
        assert len(active_agents) == 1

    async def test_list_agents_pagination(self, async_session):
        """Test agent list pagination."""
        service = AgentService(async_session)

        # Create multiple agents
        for i in range(15):
            await service.create_agent(AgentCreate(
                agent_type=AgentType.BASE,
                name=f"agent-{i}",
                capabilities=[]
            ))

        # Test limit
        first_page = await service.list_agents(limit=10, offset=0)
        second_page = await service.list_agents(limit=10, offset=10)

        assert len(first_page) == 10
        assert len(second_page) == 5

    async def test_list_agents_invalid_limit(self, async_session):
        """Test pagination validation."""
        service = AgentService(async_session)

        with pytest.raises(ValueError, match="Limit cannot exceed 1000"):
            await service.list_agents(limit=1001)

        with pytest.raises(ValueError, match="Limit must be at least 1"):
            await service.list_agents(limit=0)

        with pytest.raises(ValueError, match="Offset cannot be negative"):
            await service.list_agents(offset=-1)

    async def test_delete_agent_success(self, async_session):
        """Test successful agent deletion."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="to-delete",
            capabilities=[]
        ))

        # Verify agent exists
        assert await service.get_agent(agent.agent_id) is not None

        # Delete agent
        result = await service.delete_agent(agent.agent_id)
        assert result is True

        # Verify agent is gone
        assert await service.get_agent(agent.agent_id) is None

    async def test_delete_agent_not_found(self, async_session):
        """Test deleting non-existent agent."""
        service = AgentService(async_session)

        result = await service.delete_agent(uuid4())
        assert result is False

    async def test_count_agents(self, async_session):
        """Test counting agents."""
        service = AgentService(async_session)

        # Create agents of different types
        await service.create_agent(AgentCreate(agent_type=AgentType.BASE, name="a1", capabilities=[]))
        await service.create_agent(AgentCreate(agent_type=AgentType.BASE, name="a2", capabilities=[]))
        await service.create_agent(AgentCreate(agent_type=AgentType.EVAL, name="e1", capabilities=[]))

        total_count = await service.count_agents()
        base_count = await service.count_agents(agent_type=AgentType.BASE)
        eval_count = await service.count_agents(agent_type=AgentType.EVAL)

        assert total_count == 3
        assert base_count == 2
        assert eval_count == 1


@pytest.mark.asyncio
class TestAgentStateManagement:
    """Test agent state transitions and lifecycle operations."""

    async def test_start_agent(self, async_session):
        """Test starting an agent."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="idle-agent",
            capabilities=[]
        ))

        assert agent.state == AgentState.IDLE.value

        started = await service.start_agent(agent.agent_id)
        assert started is not None
        assert started.state == AgentState.ACTIVE.value

    async def test_pause_agent(self, async_session):
        """Test pausing an active agent."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="active-agent",
            capabilities=[]
        ))

        # Start first
        await service.start_agent(agent.agent_id)

        # Then pause
        paused = await service.pause_agent(agent.agent_id)
        assert paused is not None
        assert paused.state == AgentState.PAUSED.value

    async def test_resume_agent(self, async_session):
        """Test resuming a paused agent."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="pausable-agent",
            capabilities=[]
        ))

        # Start and pause
        await service.start_agent(agent.agent_id)
        await service.pause_agent(agent.agent_id)

        # Resume
        resumed = await service.resume_agent(agent.agent_id)
        assert resumed is not None
        assert resumed.state == AgentState.ACTIVE.value

    async def test_terminate_agent(self, async_session):
        """Test terminating an agent."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="terminatable-agent",
            capabilities=[]
        ))

        # Give agent a task
        task_id = uuid4()
        await service.assign_task(agent.agent_id, task_id)

        # Terminate
        terminated = await service.terminate_agent(agent.agent_id)
        assert terminated is not None
        assert terminated.state == AgentState.TERMINATED.value
        assert terminated.current_task_id is None  # Task cleared

    async def test_terminate_non_existent_agent(self, async_session):
        """Test terminating non-existent agent returns None."""
        service = AgentService(async_session)

        result = await service.terminate_agent(uuid4())
        assert result is None


@pytest.mark.asyncio
class TestAgentUpdates:
    """Test agent property updates."""

    async def test_update_agent_state(self, async_session):
        """Test updating agent state."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="updatable-agent",
            capabilities=[]
        ))

        updated = await service.update_agent(
            agent.agent_id,
            AgentUpdate(state=AgentState.ACTIVE)
        )

        assert updated is not None
        assert updated.state == AgentState.ACTIVE.value

    async def test_update_agent_capabilities(self, async_session):
        """Test updating agent capabilities."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="learner-agent",
            capabilities=["read"]
        ))

        updated = await service.update_agent(
            agent.agent_id,
            AgentUpdate(capabilities=["read", "write", "analyze"])
        )

        assert updated is not None
        assert set(updated.capabilities) == {"read", "write", "analyze"}

    async def test_update_agent_config(self, async_session):
        """Test updating agent configuration."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="reconfigurable-agent",
            capabilities=[],
            config=AgentConfig(max_concurrent_tasks=1)
        ))

        new_config = AgentConfig(
            max_concurrent_tasks=5,
            heartbeat_interval=60,
            task_timeout=600
        )

        updated = await service.update_agent(
            agent.agent_id,
            AgentUpdate(config=new_config)
        )

        assert updated is not None
        assert updated.config["max_concurrent_tasks"] == 5
        assert updated.config["heartbeat_interval"] == 60

    async def test_update_non_existent_agent(self, async_session):
        """Test updating non-existent agent returns None."""
        service = AgentService(async_session)

        result = await service.update_agent(
            uuid4(),
            AgentUpdate(state=AgentState.ACTIVE)
        )

        assert result is None


@pytest.mark.asyncio
class TestAgentTasks:
    """Test agent task assignment and completion."""

    async def test_assign_task_success(self, async_session):
        """Test successful task assignment."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="worker-agent",
            capabilities=["process"]
        ))

        task_id = uuid4()
        updated = await service.assign_task(agent.agent_id, task_id)

        assert updated is not None
        assert updated.current_task_id == task_id

    async def test_assign_task_to_busy_agent(self, async_session):
        """Test task assignment fails when agent has task."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="busy-agent",
            capabilities=[]
        ))

        # Assign first task
        task1 = uuid4()
        await service.assign_task(agent.agent_id, task1)

        # Try to assign second task
        task2 = uuid4()
        with pytest.raises(ValueError, match="already has task"):
            await service.assign_task(agent.agent_id, task2)

    async def test_assign_task_to_unavailable_state(self, async_session):
        """Test task assignment fails for unavailable agents."""
        service = AgentService(async_session)

        # Create paused agent
        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="paused-agent",
            capabilities=[]
        ))
        await service.pause_agent(agent.agent_id)

        # Try to assign task
        task_id = uuid4()
        with pytest.raises(ValueError, match="not available"):
            await service.assign_task(agent.agent_id, task_id)

    async def test_complete_task(self, async_session):
        """Test marking agent's task as complete."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="task-agent",
            capabilities=[]
        ))

        # Assign task
        task_id = uuid4()
        await service.assign_task(agent.agent_id, task_id)

        # Complete task
        updated = await service.complete_task(agent.agent_id)

        assert updated is not None
        assert updated.current_task_id is None

    async def test_complete_task_with_result(self, async_session):
        """Test completing task with result."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="result-agent",
            capabilities=[]
        ))

        task_id = uuid4()
        await service.assign_task(agent.agent_id, task_id)

        result = {"status": "success", "output": "task completed"}
        updated = await service.complete_task(agent.agent_id, result=result)

        assert updated is not None
        assert updated.current_task_id is None


@pytest.mark.asyncio
class TestAgentHeartbeat:
    """Test agent heartbeat mechanism."""

    async def test_register_heartbeat(self, async_session):
        """Test registering agent heartbeat."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="heartbeat-agent",
            capabilities=[]
        ))

        heartbeat = AgentHeartbeat(
            agent_id=agent.agent_id,
            state=AgentState.ACTIVE,
            current_task_id=uuid4()
        )

        updated = await service.register_heartbeat(heartbeat)

        assert updated is not None
        assert updated.state == AgentState.ACTIVE.value
        # Heartbeat time should be recent (within last second)
        assert (datetime.utcnow() - updated.last_heartbeat).total_seconds() < 1

    async def test_heartbeat_updates_state(self, async_session):
        """Test heartbeat updates agent state if different."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="state-changing-agent",
            capabilities=[]
        ))

        # Register heartbeat with different state
        heartbeat = AgentHeartbeat(
            agent_id=agent.agent_id,
            state=AgentState.ACTIVE,
            current_task_id=uuid4()
        )

        updated = await service.register_heartbeat(heartbeat)

        assert updated is not None
        assert updated.state == AgentState.ACTIVE.value


@pytest.mark.asyncio
class TestAgentMetrics:
    """Test agent performance metrics."""

    async def test_get_agent_metrics(self, async_session):
        """Test retrieving agent metrics."""
        service = AgentService(async_session)

        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="metric-agent",
            capabilities=[]
        ))

        metrics = await service.get_agent_metrics(agent.agent_id)

        assert metrics is not None
        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 0
        assert metrics.avg_task_duration == 0.0
        assert metrics.success_rate == 0.0

    async def test_get_metrics_non_existent_agent(self, async_session):
        """Test getting metrics for non-existent agent."""
        service = AgentService(async_session)

        metrics = await service.get_agent_metrics(uuid4())
        assert metrics is None


@pytest.mark.asyncio
class TestInactiveAgents:
    """Test inactive agent detection."""

    async def test_check_inactive_agents(self, async_session):
        """Test detecting inactive agents based on heartbeat timeout."""
        service = AgentService(async_session)

        # Create an agent with old heartbeat
        agent = await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="stale-agent",
            capabilities=[]
        ))

        # Manually set old heartbeat
        repo = AgentRepository(async_session)
        old_time = datetime.utcnow() - timedelta(seconds=400)
        await repo.update_heartbeat_time(agent.agent_id, old_time)

        # Check for inactive agents (timeout 300s)
        inactive = await service.check_inactive_agents(timeout_seconds=300)

        assert len(inactive) == 1
        assert inactive[0].agent_id == agent.agent_id

    async def test_check_inactive_agents_all_active(self, async_session):
        """Test when all agents are active."""
        service = AgentService(async_session)

        # Create fresh agent
        await service.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="fresh-agent",
            capabilities=[]
        ))

        # Check for inactive agents
        inactive = await service.check_inactive_agents(timeout_seconds=300)

        assert len(inactive) == 0


@pytest.mark.asyncio
class TestAgentRepository:
    """Direct repository layer tests."""

    async def test_repository_create_agent(self, async_session):
        """Test repository agent creation."""
        repo = AgentRepository(async_session)

        agent_data = AgentCreate(
            agent_type=AgentType.RESEARCH,
            name="repo-test-agent",
            capabilities=["search"]
        )

        agent = await repo.create_agent(agent_data)

        assert agent.agent_id is not None
        assert agent.name == "repo-test-agent"

    async def test_repository_get_inactive_agents(self, async_session):
        """Test repository inactive agent query."""
        repo = AgentRepository(async_session)

        # Create agent
        agent = await repo.create_agent(AgentCreate(
            agent_type=AgentType.BASE,
            name="inactive-test",
            capabilities=[]
        ))

        # Set old heartbeat
        old_time = datetime.utcnow() - timedelta(seconds=400)
        await repo.update_heartbeat_time(agent.agent_id, old_time)

        # Query inactive
        inactive = await repo.get_inactive_agents(timeout_seconds=300)

        assert len(inactive) == 1
        assert inactive[0].agent_id == agent.agent_id
