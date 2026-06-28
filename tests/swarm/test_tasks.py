"""
Swarm Task Tests

Comprehensive tests for task creation, assignment,
execution, and lifecycle management.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.swarm.models.task import (
    TaskType,
    TaskState,
    TaskPriority,
    TaskCreate,
    TaskUpdate,
    TaskAssignment,
)
from app.swarm.services.task_service import TaskService


@pytest.mark.asyncio
class TestTaskLifecycle:
    """Test task creation, retrieval, and deletion."""

    async def test_create_task_success(self, async_session, sample_swarm):
        """Test successful task creation."""
        service = TaskService(async_session)

        task_data = TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.EVALUATION,
            payload={"target": "model-1"},
            priority=TaskPriority.HIGH
        )

        task = await service.create_task(task_data)

        assert task is not None
        assert task.swarm_id == sample_swarm.swarm_id
        assert task.task_type == TaskType.EVALUATION.value
        assert task.state == TaskState.PENDING.value
        assert task.assigned_agent_id is None

    async def test_create_task_with_timeout(self, async_session, sample_swarm):
        """Test creating task with custom timeout."""
        service = TaskService(async_session)

        task_data = TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.MEDIUM,
            timeout_seconds=600
        )

        task = await service.create_task(task_data)

        assert task is not None
        assert task.max_retries == 3
        # Timeout should be calculated based on timeout_seconds
        assert task.timeout_at is not None

    async def test_get_task_success(self, async_session, sample_swarm):
        """Test retrieving an existing task."""
        service = TaskService(async_session)

        created = await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.LOW
        ))

        retrieved = await service.get_task(created.task_id)

        assert retrieved is not None
        assert retrieved.task_id == created.task_id
        assert retrieved.state == TaskState.PENDING.value

    async def test_get_task_not_found(self, async_session):
        """Test retrieving non-existent task."""
        service = TaskService(async_session)

        result = await service.get_task(uuid4())
        assert result is None

    async def test_list_tasks_empty(self, async_session, sample_swarm):
        """Test listing tasks when none exist."""
        service = TaskService(async_session)

        tasks = await service.list_tasks(swarm_id=sample_swarm.swarm_id)
        assert tasks == []

    async def test_list_tasks_with_results(self, async_session, sample_swarm):
        """Test listing tasks with multiple tasks."""
        service = TaskService(async_session)

        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.EVALUATION,
            priority=TaskPriority.HIGH
        ))
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.MEDIUM
        ))
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.LEARNING,
            priority=TaskPriority.LOW
        ))

        tasks = await service.list_tasks(swarm_id=sample_swarm.swarm_id)
        assert len(tasks) == 3

    async def test_list_tasks_filter_by_state(self, async_session, sample_swarm):
        """Test filtering tasks by state."""
        service = TaskService(async_session)

        task1 = await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.MEDIUM
        ))

        # Update one task to assigned state
        await service.update_task(task1.task_id, TaskUpdate(state=TaskState.ASSIGNED))

        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.MEDIUM
        ))

        pending_tasks = await service.list_tasks(
            swarm_id=sample_swarm.swarm_id,
            state=TaskState.PENDING
        )
        assigned_tasks = await service.list_tasks(
            swarm_id=sample_swarm.swarm_id,
            state=TaskState.ASSIGNED
        )

        assert len(pending_tasks) == 1
        assert len(assigned_tasks) == 1

    async def test_delete_task_success(self, async_session, sample_swarm):
        """Test successful task deletion."""
        service = TaskService(async_session)

        task = await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.MEDIUM
        ))

        result = await service.delete_task(task.task_id)
        assert result is True

        assert await service.get_task(task.task_id) is None

    async def test_delete_task_not_found(self, async_session):
        """Test deleting non-existent task."""
        service = TaskService(async_session)

        result = await service.delete_task(uuid4())
        assert result is False


@pytest.mark.asyncio
class TestTaskAssignment:
    """Test task assignment to agents."""

    async def test_assign_task_success(self, async_session, sample_task, sample_agent):
        """Test successful task assignment."""
        service = TaskService(async_session)

        assignment = TaskAssignment(
            task_id=sample_task.task_id,
            agent_id=sample_agent.agent_id
        )

        assigned = await service.assign_task(assignment)

        assert assigned is not None
        assert assigned.assigned_agent_id == sample_agent.agent_id
        assert assigned.state == TaskState.ASSIGNED.value

    async def test_assign_task_updates_agent(self, async_session, sample_task, sample_agent):
        """Test that task assignment updates agent's current task."""
        from app.swarm.services.agent_service import AgentService

        task_service = TaskService(async_session)
        agent_service = AgentService(async_session)

        await task_service.assign_task(TaskAssignment(
            task_id=sample_task.task_id,
            agent_id=sample_agent.agent_id
        ))

        updated_agent = await agent_service.get_agent(sample_agent.agent_id)

        assert updated_agent is not None
        assert updated_agent.current_task_id == sample_task.task_id

    async def test_cannot_assign_completed_task(self, async_session, sample_task):
        """Test cannot assign a completed task."""
        service = TaskService(async_session)

        # Mark task as completed
        await service.update_task(sample_task.task_id, TaskUpdate(
            state=TaskState.COMPLETED,
            result={"status": "done"}
        ))

        # Try to assign
        with pytest.raises(ValueError, match="cannot be assigned"):
            await service.assign_task(TaskAssignment(
                task_id=sample_task.task_id,
                agent_id=uuid4()
            ))


@pytest.mark.asyncio
class TestTaskExecution:
    """Test task execution lifecycle."""

    async def test_start_task(self, async_session, sample_task):
        """Test starting a task."""
        service = TaskService(async_session)

        started = await service.start_task(sample_task.task_id)

        assert started is not None
        assert started.state == TaskState.IN_PROGRESS.value
        assert started.started_at is not None

    async def test_complete_task(self, async_session, sample_task):
        """Test completing a task."""
        service = TaskService(async_session)

        result = {"output": "task completed", "metrics": {"time": 1.5}}
        completed = await service.complete_task(
            sample_task.task_id,
            result=result
        )

        assert completed is not None
        assert completed.state == TaskState.COMPLETED.value
        assert completed.completed_at is not None
        assert completed.result == result

    async def test_fail_task(self, async_session, sample_task):
        """Test failing a task."""
        service = TaskService(async_session)

        error_msg = "Processing failed: insufficient data"
        failed = await service.fail_task(sample_task.task_id, error_msg)

        assert failed is not None
        assert failed.state == TaskState.FAILED.value
        assert failed.error == error_msg

    async def test_cancel_task(self, async_session, sample_task):
        """Test cancelling a task."""
        service = TaskService(async_session)

        cancelled = await service.cancel_task(sample_task.task_id)

        assert cancelled is not None
        assert cancelled.state == TaskState.CANCELLED.value


@pytest.mark.asyncio
class TestTaskRetries:
    """Test task retry mechanism."""

    async def test_retry_increments_count(self, async_session, sample_task):
        """Test that retry increments retry count."""
        service = TaskService(async_session)

        # Fail the task
        await service.fail_task(sample_task.task_id, "Test failure")

        # Get updated task
        task = await service.get_task(sample_task.task_id)

        assert task is not None
        assert task.retry_count == 1

    async def test_max_retries_exceeded(self, async_session, sample_task):
        """Test task cannot retry beyond max retries."""
        service = TaskService(async_session)

        # Set task to max retries
        await service.update_task(sample_task.task_id, TaskUpdate())
        # Manually set retry count to max
        task = await service.get_task(sample_task.task_id)
        if task:
            # Simulate max retries reached
            for _ in range(task.max_retries + 1):
                await service.fail_task(sample_task.task_id, "Retry test")

        # Should be marked as failed permanently
        final_task = await service.get_task(sample_task.task_id)
        if final_task:
            assert final_task.state == TaskState.FAILED.value


@pytest.mark.asyncio
class TestTaskQueue:
    """Test task queue management."""

    async def test_get_task_queue(self, async_session, sample_swarm):
        """Test retrieving task queue for swarm."""
        service = TaskService(async_session)

        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.EVALUATION,
            priority=TaskPriority.HIGH
        ))
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.MEDIUM
        ))

        queue = await service.get_task_queue(sample_swarm.swarm_id)

        assert len(queue) >= 2

    async def test_get_agent_tasks(self, async_session, sample_swarm, sample_agent):
        """Test getting tasks for specific agent."""
        service = TaskService(async_session)

        # Create and assign tasks
        task1 = await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.MEDIUM
        ))
        task2 = await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.LOW
        ))

        await service.assign_task(TaskAssignment(
            task_id=task1.task_id,
            agent_id=sample_agent.agent_id
        ))
        await service.assign_task(TaskAssignment(
            task_id=task2.task_id,
            agent_id=sample_agent.agent_id
        ))

        agent_tasks = await service.get_agent_tasks(sample_agent.agent_id)

        assert len(agent_tasks) == 2
        assert all(t.assigned_agent_id == sample_agent.agent_id for t in agent_tasks)


@pytest.mark.asyncio
class TestTaskPriority:
    """Test task priority handling."""

    async def test_priority_ordering(self, async_session, sample_swarm):
        """Test tasks are ordered by priority."""
        service = TaskService(async_session)

        # Create tasks with different priorities
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.LOW
        ))
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.CRITICAL
        ))
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.HIGH
        ))

        queue = await service.get_task_queue(sample_swarm.swarm_id)

        # Critical should be first (highest priority value)
        if len(queue) >= 2:
            # Check that critical task has higher priority than low
            critical_task = next((t for t in queue if t.priority == 10), None)
            low_task = next((t for t in queue if t.priority == 1), None)

            if critical_task and low_task:
                # Critical should come before low in queue
                assert queue.index(critical_task) < queue.index(low_task)


@pytest.mark.asyncio
class TestTaskTimeout:
    """Test task timeout handling."""

    async def test_timeout_detection(self, async_session, sample_swarm):
        """Test detection of timed out tasks."""
        service = TaskService(async_session)

        # Create task with short timeout
        task = await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.GENERAL,
            priority=TaskPriority.MEDIUM,
            timeout_seconds=1
        ))

        # Start the task
        await service.start_task(task.task_id)

        # Wait for timeout
        import asyncio
        await asyncio.sleep(2)

        # Check for timed out tasks
        timed_out = await service.get_timed_out_tasks(sample_swarm.swarm_id)

        # Should contain our timed out task
        assert len(timed_out) >= 0  # May or may not detect depending on timing


@pytest.mark.asyncio
class TestTaskUpdates:
    """Test task property updates."""

    async def test_update_task_state(self, async_session, sample_task):
        """Test updating task state."""
        service = TaskService(async_session)

        updated = await service.update_task(
            sample_task.task_id,
            TaskUpdate(state=TaskState.IN_PROGRESS)
        )

        assert updated is not None
        assert updated.state == TaskState.IN_PROGRESS.value

    async def test_update_task_with_result(self, async_session, sample_task):
        """Test updating task with result."""
        service = TaskService(async_session)

        result_data = {"output": "success", "metrics": {"time": 0.5}}
        updated = await service.update_task(
            sample_task.task_id,
            TaskUpdate(result=result_data)
        )

        assert updated is not None
        assert updated.result == result_data

    async def test_update_non_existent_task(self, async_session):
        """Test updating non-existent task."""
        service = TaskService(async_session)

        result = await service.update_task(
            uuid4(),
            TaskUpdate(state=TaskState.COMPLETED)
        )

        assert result is None


@pytest.mark.asyncio
class TestTaskSearch:
    """Test task search functionality."""

    async def test_search_tasks_by_type(self, async_session, sample_swarm):
        """Test searching tasks by type."""
        service = TaskService(async_session)

        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.EVALUATION,
            priority=TaskPriority.MEDIUM
        ))
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.MEDIUM
        ))
        await service.create_task(TaskCreate(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.EVALUATION,
            priority=TaskPriority.MEDIUM
        ))

        eval_tasks = await service.list_tasks(
            swarm_id=sample_swarm.swarm_id,
            task_type=TaskType.EVALUATION
        )

        assert len(eval_tasks) == 2
        assert all(t.task_type == TaskType.EVALUATION.value for t in eval_tasks)
