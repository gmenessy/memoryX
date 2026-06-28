"""
Swarm Tests

Comprehensive tests for swarm lifecycle, agent management,
and orchestration within the swarm system.
"""
import pytest
from uuid import uuid4

from app.swarm.models.swarm import (
    SwarmType,
    SwarmState,
    SwarmCreate,
    SwarmUpdate,
    SwarmConfig,
)
from app.swarm.services.swarm_service import SwarmService


@pytest.mark.asyncio
class TestSwarmLifecycle:
    """Test swarm creation, retrieval, and deletion."""

    async def test_create_swarm_success(self, async_session):
        """Test successful swarm creation."""
        service = SwarmService(async_session)

        swarm_data = SwarmCreate(
            name="test-swarm",
            swarm_type=SwarmType.EVAL,
            config=SwarmConfig(max_agents=5, coordination_pattern="hierarchical")
        )

        swarm = await service.create_swarm(swarm_data)

        assert swarm is not None
        assert swarm.name == "test-swarm"
        assert swarm.swarm_type == SwarmType.EVAL.value
        assert swarm.state == SwarmState.IDLE.value
        assert len(swarm.agent_ids) == 0

    async def test_create_swarm_with_initial_agents(self, async_session):
        """Test creating swarm with initial agent count."""
        from app.swarm.services.agent_service import AgentService

        swarm_service = SwarmService(async_session)
        agent_service = AgentService(async_session)

        swarm_data = SwarmCreate(
            name="agent-swarm",
            swarm_type=SwarmType.RESEARCH,
            initial_agent_count=3
        )

        swarm = await swarm_service.create_swarm(swarm_data)

        # Should create 3 agents automatically
        assert len(swarm.agent_ids) == 3

    async def test_get_swarm_success(self, async_session):
        """Test retrieving an existing swarm."""
        service = SwarmService(async_session)

        created = await service.create_swarm(SwarmCreate(
            name="get-test",
            swarm_type=SwarmType.SIMULATION
        ))

        retrieved = await service.get_swarm(created.swarm_id)

        assert retrieved is not None
        assert retrieved.swarm_id == created.swarm_id
        assert retrieved.name == "get-test"

    async def test_get_swarm_not_found(self, async_session):
        """Test retrieving non-existent swarm."""
        service = SwarmService(async_session)

        result = await service.get_swarm(uuid4())
        assert result is None

    async def test_list_swarms_empty(self, async_session):
        """Test listing swarms when none exist."""
        service = SwarmService(async_session)

        swarms = await service.list_swarms()
        assert swarms == []

    async def test_list_swarms_with_results(self, async_session):
        """Test listing swarms with multiple swarms."""
        service = SwarmService(async_session)

        await service.create_swarm(SwarmCreate(
            name="swarm-1",
            swarm_type=SwarmType.EVAL
        ))
        await service.create_swarm(SwarmCreate(
            name="swarm-2",
            swarm_type=SwarmType.RESEARCH
        ))
        await service.create_swarm(SwarmCreate(
            name="swarm-3",
            swarm_type=SwarmType.LEARNING
        ))

        swarms = await service.list_swarms()
        assert len(swarms) == 3

    async def test_list_swarms_filter_by_type(self, async_session):
        """Test filtering swarms by type."""
        service = SwarmService(async_session)

        await service.create_swarm(SwarmCreate(
            name="eval-1",
            swarm_type=SwarmType.EVAL
        ))
        await service.create_swarm(SwarmCreate(
            name="research-1",
            swarm_type=SwarmType.RESEARCH
        ))
        await service.create_swarm(SwarmCreate(
            name="eval-2",
            swarm_type=SwarmType.EVAL
        ))

        eval_swarms = await service.list_swarms(swarm_type=SwarmType.EVAL)
        research_swarms = await service.list_swarms(swarm_type=SwarmType.RESEARCH)

        assert len(eval_swarms) == 2
        assert len(research_swarms) == 1

    async def test_list_swarms_filter_by_state(self, async_session):
        """Test filtering swarms by state."""
        service = SwarmService(async_session)

        swarm1 = await service.create_swarm(SwarmCreate(
            name="idle-swarm",
            swarm_type=SwarmType.EVAL
        ))
        swarm2 = await service.create_swarm(SwarmCreate(
            name="running-swarm",
            swarm_type=SwarmType.EVAL
        ))

        # Start one swarm
        await service.start_swarm(swarm2.swarm_id)

        idle_swarms = await service.list_swarms(state=SwarmState.IDLE)
        running_swarms = await service.list_swarms(state=SwarmState.RUNNING)

        assert len(idle_swarms) == 1
        assert len(running_swarms) == 1

    async def test_delete_swarm_success(self, async_session):
        """Test successful swarm deletion."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="to-delete",
            swarm_type=SwarmType.EVAL
        ))

        result = await service.delete_swarm(swarm.swarm_id)
        assert result is True

        assert await service.get_swarm(swarm.swarm_id) is None

    async def test_delete_swarm_not_found(self, async_session):
        """Test deleting non-existent swarm."""
        service = SwarmService(async_session)

        result = await service.delete_swarm(uuid4())
        assert result is False


@pytest.mark.asyncio
class TestSwarmStateManagement:
    """Test swarm state transitions and lifecycle operations."""

    async def test_start_swarm(self, async_session):
        """Test starting a swarm."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="startable-swarm",
            swarm_type=SwarmType.EVAL
        ))

        assert swarm.state == SwarmState.IDLE.value

        started = await service.start_swarm(swarm.swarm_id)
        assert started is not None
        assert started.state == SwarmState.RUNNING.value
        assert started.started_at is not None

    async def test_pause_swarm(self, async_session):
        """Test pausing a running swarm."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="pausable-swarm",
            swarm_type=SwarmType.EVAL
        ))

        await service.start_swarm(swarm.swarm_id)

        paused = await service.pause_swarm(swarm.swarm_id)
        assert paused is not None
        assert paused.state == SwarmState.PAUSED.value

    async def test_resume_swarm(self, async_session):
        """Test resuming a paused swarm."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="resumable-swarm",
            swarm_type=SwarmType.EVAL
        ))

        await service.start_swarm(swarm.swarm_id)
        await service.pause_swarm(swarm.swarm_id)

        resumed = await service.resume_swarm(swarm.swarm_id)
        assert resumed is not None
        assert resumed.state == SwarmState.RUNNING.value

    async def test_terminate_swarm(self, async_session):
        """Test terminating a swarm."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="terminatable-swarm",
            swarm_type=SwarmType.EVAL
        ))

        await service.start_swarm(swarm.swarm_id)

        terminated = await service.terminate_swarm(swarm.swarm_id)
        assert terminated is not None
        assert terminated.state == SwarmState.TERMINATED.value
        assert terminated.stopped_at is not None


@pytest.mark.asyncio
class TestSwarmAgentManagement:
    """Test adding and removing agents from swarms."""

    async def test_add_agent_to_swarm(self, async_session):
        """Test adding an agent to a swarm."""
        from app.swarm.services.agent_service import AgentService

        swarm_service = SwarmService(async_session)
        agent_service = AgentService(async_session)

        # Create swarm and agent
        swarm = await swarm_service.create_swarm(SwarmCreate(
            name="agent-host-swarm",
            swarm_type=SwarmType.EVAL
        ))
        agent = await agent_service.create_agent(
            await agent_service.create_agent.__self__(AgentCreate(
                agent_type="base",
                name="swarm-agent",
                capabilities=[]
            ))
        )

        updated = await swarm_service.add_agent(swarm.swarm_id, agent.agent_id)

        assert updated is not None
        assert agent.agent_id in updated.agent_ids

    async def test_remove_agent_from_swarm(self, async_session):
        """Test removing an agent from a swarm."""
        from app.swarm.services.agent_service import AgentService

        swarm_service = SwarmService(async_session)
        agent_service = AgentService(async_session)

        # Create swarm with agent
        swarm = await swarm_service.create_swarm(SwarmCreate(
            name="remove-test-swarm",
            swarm_type=SwarmType.EVAL,
            initial_agent_count=1
        ))

        agent_id = swarm.agent_ids[0]

        updated = await swarm_service.remove_agent(swarm.swarm_id, agent_id)

        assert updated is not None
        assert agent_id not in updated.agent_ids

    async def test_cannot_add_duplicate_agent(self, async_session):
        """Test cannot add same agent twice."""
        from app.swarm.services.agent_service import AgentService

        swarm_service = SwarmService(async_session)
        agent_service = AgentService(async_session)

        swarm = await swarm_service.create_swarm(SwarmCreate(
            name="duplicate-test",
            swarm_type=SwarmType.EVAL
        ))

        agent = await agent_service.create_agent(
            await agent_service.create_agent.__self__(AgentCreate(
                agent_type="base",
                name="double-agent",
                capabilities=[]
            ))
        )

        # Add once
        await swarm_service.add_agent(swarm.swarm_id, agent.agent_id)

        # Try to add again
        with pytest.raises(ValueError, match="already in swarm"):
            await swarm_service.add_agent(swarm.swarm_id, agent.agent_id)


@pytest.mark.asyncio
class TestSwarmStatusAndMetrics:
    """Test swarm status and metrics retrieval."""

    async def test_get_swarm_status(self, async_session):
        """Test retrieving detailed swarm status."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="status-swarm",
            swarm_type=SwarmType.EVAL,
            initial_agent_count=3
        ))

        await service.start_swarm(swarm.swarm_id)

        status = await service.get_swarm_status(swarm.swarm_id)

        assert status is not None
        assert status.swarm_id == swarm.swarm_id
        assert status.agent_count >= 0
        assert status.state == SwarmState.RUNNING.value

    async def test_get_swarm_metrics(self, async_session):
        """Test retrieving swarm performance metrics."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="metrics-swarm",
            swarm_type=SwarmType.EVAL
        ))

        metrics = await service.get_swarm_metrics(swarm.swarm_id)

        assert metrics is not None
        assert metrics.swarm_id == swarm.swarm_id


@pytest.mark.asyncio
class TestSwarmUpdates:
    """Test swarm property updates."""

    async def test_update_swarm_config(self, async_session):
        """Test updating swarm configuration."""
        service = SwarmService(async_session)

        swarm = await service.create_swarm(SwarmCreate(
            name="reconfigurable-swarm",
            swarm_type=SwarmType.EVAL,
            config=SwarmConfig(max_agents=5)
        ))

        new_config = SwarmConfig(
            max_agents=10,
            coordination_pattern="flat",
            auto_scale=True
        )

        updated = await service.update_swarm(
            swarm.swarm_id,
            SwarmUpdate(config=new_config)
        )

        assert updated is not None
        assert updated.config["max_agents"] == 10
        assert updated.config["coordination_pattern"] == "flat"

    async def test_update_non_existent_swarm(self, async_session):
        """Test updating non-existent swarm."""
        service = SwarmService(async_session)

        result = await service.update_swarm(
            uuid4(),
            SwarmUpdate(state=SwarmState.RUNNING)
        )

        assert result is None


@pytest.mark.asyncio
class TestSwarmIntegration:
    """Test swarm integration with other components."""

    async def test_swarm_task_distribution(self, async_session):
        """Test task distribution within swarm."""
        from app.swarm.services.task_service import TaskService
        from app.swarm.services.agent_service import AgentService

        swarm_service = SwarmService(async_session)
        task_service = TaskService(async_session)
        agent_service = AgentService(async_session)

        # Create swarm with agents
        swarm = await swarm_service.create_swarm(SwarmCreate(
            name="task-dist-swarm",
            swarm_type=SwarmType.EVAL,
            initial_agent_count=2
        ))

        # Create tasks
        from app.swarm.models.task import TaskCreate
        task1 = await task_service.create_task(TaskCreate(
            swarm_id=swarm.swarm_id,
            title="task-1",
            task_type="process",
            priority="medium"
        ))
        task2 = await task_service.create_task(TaskCreate(
            swarm_id=swarm.swarm_id,
            title="task-2",
            task_type="analyze",
            priority="high"
        ))

        # Get queue - should have 2 tasks
        queue = await task_service.get_task_queue(swarm.swarm_id)
        assert len(queue) == 2
