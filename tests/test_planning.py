"""
Planning System Tests

Tests for the Planning Engine including goal decomposition,
plan execution, and replanning.
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.models.planning import (
    PlanCreate,
    PlanStatus,
    TaskStatus,
    TaskPriority,
    PlanExecutionRequest,
)
from app.services.planning_service import PlanningService


@pytest.mark.asyncio
async def test_create_plan_with_decomposition(db_session):
    """Test plan creation with automatic goal decomposition."""
    service = PlanningService(db_session)

    plan_data = PlanCreate(
        agent_id="test-agent",
        goal="Search for information about AI"
    )

    plan = await service.create_plan(plan_data)

    assert plan is not None
    assert plan.agent_id == "test-agent"
    assert plan.status == PlanStatus.DRAFT
    assert "search" in plan.goal.lower()
    assert plan.plan_id is not None


@pytest.mark.asyncio
async def test_get_plan(db_session):
    """Test retrieving a plan by ID."""
    service = PlanningService(db_session)

    plan_data = PlanCreate(
        agent_id="test-agent",
        goal="Create a report"
    )

    created_plan = await service.create_plan(plan_data)
    retrieved_plan = await service.get_plan(created_plan.plan_id)

    assert retrieved_plan is not None
    assert retrieved_plan.plan_id == created_plan.plan_id
    assert retrieved_plan.goal == created_plan.goal


@pytest.mark.asyncio
async def test_get_agent_plans(db_session):
    """Test retrieving all plans for an agent."""
    service = PlanningService(db_session)

    # Create multiple plans
    await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Plan 1"
    ))
    await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Plan 2"
    ))
    await service.create_plan(PlanCreate(
        agent_id="other-agent",
        goal="Plan 3"
    ))

    # Get plans for test-agent
    plans = await service.get_agent_plans("test-agent")

    assert len(plans) == 2
    assert all(plan.agent_id == "test-agent" for plan in plans)


@pytest.mark.asyncio
async def test_update_plan_status(db_session):
    """Test updating plan status and progress."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Test plan"
    ))

    updated_plan = await service.update_plan_status(
        plan.plan_id,
        PlanStatus.IN_PROGRESS,
        0.5
    )

    assert updated_plan is not None
    assert updated_plan.status == PlanStatus.IN_PROGRESS
    assert updated_plan.progress == 0.5


@pytest.mark.asyncio
async def test_create_task(db_session):
    """Test creating a task."""
    service = PlanningService(db_session)

    # First create a plan
    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Test goal"
    ))

    # Create a task
    from app.models.planning import TaskCreate
    task = await service.create_task(TaskCreate(
        plan_id=plan.plan_id,
        title="Test Task",
        task_type="test",
        parameters={"key": "value"}
    ))

    assert task is not None
    assert task.title == "Test Task"
    assert task.plan_id == plan.plan_id
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_plan_tasks(db_session):
    """Test retrieving all tasks for a plan."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Generate content"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)

    assert len(tasks) > 0
    assert all(task.plan_id == plan.plan_id for task in tasks)


@pytest.mark.asyncio
async def test_update_task_status(db_session):
    """Test updating task status."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Test goal"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)
    if not tasks:
        pytest.skip("No tasks created")

    updated_task = await service.update_task_status(
        tasks[0].task_id,
        TaskStatus.COMPLETED,
        result={"success": True}
    )

    assert updated_task is not None
    assert updated_task.status == TaskStatus.COMPLETED
    assert updated_task.result is not None


@pytest.mark.asyncio
async def test_execute_plan(db_session):
    """Test executing a plan."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Execute this plan"
    ))

    execution_request = PlanExecutionRequest(
        plan_id=plan.plan_id,
        max_parallel_tasks=2,
        continue_on_failure=True
    )

    result = await service.execute_plan(execution_request)

    assert result is not None
    assert result.plan_id == plan.plan_id
    assert result.total_tasks > 0
    assert result.status in [PlanStatus.COMPLETED, PlanStatus.FAILED]


@pytest.mark.asyncio
async def test_execute_plan_with_failure_handling(db_session):
    """Test plan execution with failure handling."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Test failure handling"
    ))

    execution_request = PlanExecutionRequest(
        plan_id=plan.plan_id,
        max_parallel_tasks=1,
        continue_on_failure=False
    )

    result = await service.execute_plan(execution_request)

    assert result is not None
    assert result.execution_duration >= 0


@pytest.mark.asyncio
async def test_replan_on_failure(db_session):
    """Test replanning after failure."""
    service = PlanningService(db_session)

    # Create and execute a plan
    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Original plan"
    ))

    # Mark as failed
    await service.update_plan_status(plan.plan_id, PlanStatus.FAILED, 0.0)

    # Create replan
    replan = await service.replan_on_failure(plan.plan_id, max_retries=3)

    assert replan is not None
    assert replan.parent_plan_id == plan.plan_id
    assert "Retry" in replan.goal
    assert replan.plan_data.get("retry_count") == 1


@pytest.mark.asyncio
async def test_replan_max_retries_exceeded(db_session):
    """Test that replanning stops after max retries."""
    service = PlanningService(db_session)

    plan_data = PlanCreate(
        agent_id="test-agent",
        goal="Test plan"
    )
    plan_data.plan_data = {"retry_count": 5}

    plan = await service.create_plan(plan_data)
    await service.update_plan_status(plan.plan_id, PlanStatus.FAILED, 0.0)

    # Try to replan when retries exceeded
    replan = await service.replan_on_failure(plan.plan_id, max_retries=3)

    assert replan is None


@pytest.mark.asyncio
async def test_get_plan_history(db_session):
    """Test retrieving plan history."""
    service = PlanningService(db_session)

    agent_id = "test-agent"

    # Create initial plan
    plan1 = await service.create_plan(PlanCreate(
        agent_id=agent_id,
        goal="Initial plan"
    ))

    # Create replan
    plan2 = await service.replan_on_failure(plan1.plan_id, max_retries=3)

    if plan2:
        history = await service.get_plan_history(agent_id)

        assert len(history) >= 2
        assert any(p.plan_id == plan1.plan_id for p in history)
        assert any(p.plan_id == plan2.plan_id for p in history)


@pytest.mark.asyncio
async def test_goal_decomposition_search(db_session):
    """Test goal decomposition for search-type goals."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Search for python tutorials"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)

    assert len(tasks) >= 3
    task_types = [task.task_type for task in tasks]
    assert "query" in task_types
    assert "search" in task_types


@pytest.mark.asyncio
async def test_goal_decomposition_create(db_session):
    """Test goal decomposition for creation-type goals."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Create a presentation"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)

    assert len(tasks) >= 4
    task_types = [task.task_type for task in tasks]
    assert "analyze" in task_types
    assert "generate" in task_types


@pytest.mark.asyncio
async def test_goal_decomposition_analyze(db_session):
    """Test goal decomposition for analysis-type goals."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Analyze the data"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)

    assert len(tasks) >= 3
    task_titles = [task.title.lower() for task in tasks]
    assert any("load" in title for title in task_titles)
    assert any("analyze" in title for title in task_titles)


@pytest.mark.asyncio
async def test_goal_decomposition_generic(db_session):
    """Test generic goal decomposition."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Do something complex"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)

    assert len(tasks) >= 4
    task_types = [task.task_type for task in tasks]
    assert "analyze" in task_types
    assert "execute" in task_types


@pytest.mark.asyncio
async def test_plan_progress_calculation(db_session):
    """Test that plan progress is calculated correctly."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Test progress calculation"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)
    if len(tasks) < 2:
        pytest.skip("Need at least 2 tasks")

    # Complete first task
    await service.update_task_status(tasks[0].task_id, TaskStatus.COMPLETED)

    # Get updated plan
    updated_plan = await service.get_plan(plan.plan_id)

    assert updated_plan.progress > 0
    assert updated_plan.completed_tasks == 1


@pytest.mark.asyncio
async def test_parallel_task_execution(db_session):
    """Test that tasks are executed with limited parallelism."""
    service = PlanningService(db_session)

    plan = await service.create_plan(PlanCreate(
        agent_id="test-agent",
        goal="Execute parallel tasks"
    ))

    tasks = await service.get_plan_tasks(plan.plan_id)
    if len(tasks) < 2:
        pytest.skip("Need at least 2 tasks")

    execution_request = PlanExecutionRequest(
        plan_id=plan.plan_id,
        max_parallel_tasks=2,
        continue_on_failure=True
    )

    result = await service.execute_plan(execution_request)

    assert result.total_tasks == len(tasks)
    assert result.completed_tasks + result.failed_tasks == len(tasks)


# Integration Tests


@pytest.mark.asyncio
async def test_full_planning_workflow(db_session):
    """Test complete planning workflow from creation to execution."""
    service = PlanningService(db_session)

    # 1. Create plan with goal
    plan = await service.create_plan(PlanCreate(
        agent_id="workflow-agent",
        goal="Complete a complex task"
    ))
    assert plan.status == PlanStatus.DRAFT

    # 2. Get decomposed tasks
    tasks = await service.get_plan_tasks(plan.plan_id)
    assert len(tasks) > 0

    # 3. Execute the plan
    execution_request = PlanExecutionRequest(
        plan_id=plan.plan_id,
        max_parallel_tasks=3,
        continue_on_failure=True
    )

    result = await service.execute_plan(execution_request)
    assert result.total_tasks == len(tasks)

    # 4. Check final plan status
    final_plan = await service.get_plan(plan.plan_id)
    assert final_plan.status in [PlanStatus.COMPLETED, PlanStatus.FAILED]
    assert final_plan.completed_at is not None


@pytest.mark.asyncio
async def test_replanning_workflow(db_session):
    """Test replanning workflow with learning."""
    service = PlanningService(db_session)

    # 1. Create original plan
    original_plan = await service.create_plan(PlanCreate(
        agent_id="learning-agent",
        goal="Learn from failure"
    ))

    # 2. Execute and mark as failed
    await service.execute_plan(PlanExecutionRequest(
        plan_id=original_plan.plan_id,
        max_parallel_tasks=1
    ))

    # 3. Mark as failed
    await service.update_plan_status(original_plan.plan_id, PlanStatus.FAILED, 0.0)

    # 4. Create replan with learning
    replan = await service.replan_on_failure(original_plan.plan_id, max_retries=3)

    assert replan is not None
    assert replan.parent_plan_id == original_plan.plan_id
    assert "learned_from" in replan.plan_data
    assert "adjustments" in replan.plan_data

    # 5. Execute the replan
    replan_result = await service.execute_plan(PlanExecutionRequest(
        plan_id=replan.plan_id,
        max_parallel_tasks=2
    ))

    assert replan_result.total_tasks > 0
