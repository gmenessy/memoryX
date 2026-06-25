"""
Planning Service - Business Logic Layer for Decision Making

The Planning Engine provides goal decomposition, task planning,
and execution tracking for AI agents.
"""
from datetime import datetime
from typing import Any
from uuid import UUID
from collections import defaultdict
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger, log_service_action, log_error
from app.models.planning import (
    PlanCreate,
    PlanUpdate,
    PlanResponse,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    PlanStatus,
    TaskStatus,
    TaskPriority,
    PlanExecutionRequest,
    PlanExecutionResult,
)
from app.repositories.planning_repository import PlanRepository, TaskRepository

logger = get_logger(__name__)


class PlanningService:
    """
    Service for Planning operations.
    Implements goal decomposition and plan execution.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plan_repo = PlanRepository(session)
        self.task_repo = TaskRepository(session)

    # Plan Management

    async def create_plan(self, plan_data: PlanCreate) -> PlanResponse:
        """
        Create a new plan with automatic goal decomposition.

        Args:
            plan_data: Plan creation data

        Returns:
            Created plan with decomposed tasks
        """
        logger.info(f"Creating plan for agent {plan_data.agent_id}: {plan_data.goal}")

        try:
            # Create the plan
            plan = await self.plan_repo.create_plan(plan_data)

            # Decompose goal into tasks
            tasks = await self._decompose_goal(plan.plan_id, plan.goal, plan.plan_data)

            # Update plan with task information
            task_count = len(tasks)
            logger.info(f"Plan {plan.plan_id} decomposed into {task_count} tasks")

            return await self.plan_repo.get_plan(plan.plan_id)

        except Exception as e:
            log_error("PlanningService.create_plan", e, agent_id=plan_data.agent_id, goal=plan_data.goal)
            raise

    async def get_plan(self, plan_id: UUID) -> PlanResponse | None:
        """Get plan by ID with current progress."""
        return await self.plan_repo.get_plan(plan_id)

    async def get_agent_plans(
        self,
        agent_id: str,
        status: PlanStatus | None = None
    ) -> list[PlanResponse]:
        """Get all plans for an agent."""
        return await self.plan_repo.get_agent_plans(agent_id, status)

    async def update_plan_status(
        self,
        plan_id: UUID,
        status: PlanStatus,
        progress: float | None = None
    ) -> PlanResponse | None:
        """Update plan status and progress."""
        plan = await self.plan_repo.update_plan_status(plan_id, status, progress)

        if plan and status == PlanStatus.COMPLETED:
            logger.info(f"Plan {plan_id} completed successfully")

        return plan

    # Task Management

    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """Create a new task."""
        logger.info(f"Creating task: {task_data.title} for plan {task_data.plan_id}")
        return await self.task_repo.create_task(task_data)

    async def get_task(self, task_id: UUID) -> TaskResponse | None:
        """Get task by ID."""
        return await self.task_repo.get_task(task_id)

    async def get_plan_tasks(self, plan_id: UUID) -> list[TaskResponse]:
        """Get all tasks for a plan."""
        return await self.task_repo.get_plan_tasks(plan_id)

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error_message: str | None = None
    ) -> TaskResponse | None:
        """Update task status and result."""
        task = await self.task_repo.update_task(task_id, status, result, error_message)

        if task:
            # Update parent plan progress
            await self._update_plan_progress(task.plan_id)

        return task

    # Plan Execution

    async def execute_plan(
        self,
        request: PlanExecutionRequest
    ) -> PlanExecutionResult:
        """
        Execute a plan with its tasks.

        Args:
            request: Plan execution request

        Returns:
            Execution result
        """
        logger.info(f"Executing plan {request.plan_id}")

        # Get plan details
        plan = await self.plan_repo.get_plan(request.plan_id)
        if not plan:
            raise ValueError(f"Plan {request.plan_id} not found")

        # Update plan status to in_progress
        await self.plan_repo.update_plan_status(
            request.plan_id,
            PlanStatus.IN_PROGRESS
        )

        start_time = datetime.utcnow()
        total_tasks = 0
        completed_tasks = 0
        failed_tasks = 0
        skipped_tasks = 0
        error_summary = []

        try:
            # Get all pending tasks
            pending_tasks = await self.task_repo.get_pending_tasks(request.plan_id)
            total_tasks = len(pending_tasks)

            # Execute tasks with limited parallelism
            completed_tasks, failed_tasks, skipped_tasks = await self._execute_tasks_parallel(
                pending_tasks,
                request.max_parallel_tasks,
                request.continue_on_failure,
                error_summary
            )

            # Calculate final status
            execution_duration = (datetime.utcnow() - start_time).total_seconds()

            if failed_tasks == 0:
                final_status = PlanStatus.COMPLETED
                await self.plan_repo.update_plan_status(
                    request.plan_id,
                    final_status,
                    1.0
                )
            elif completed_tasks > 0:
                final_status = PlanStatus.FAILED
                await self.plan_repo.update_plan_status(
                    request.plan_id,
                    final_status,
                    completed_tasks / total_tasks
                )
            else:
                final_status = PlanStatus.FAILED
                await self.plan_repo.update_plan_status(
                    request.plan_id,
                    final_status,
                    0.0
                )

            logger.info(
                f"Plan execution complete: {total_tasks} tasks, "
                f"{completed_tasks} completed, {failed_tasks} failed"
            )

            return PlanExecutionResult(
                plan_id=request.plan_id,
                status=final_status,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                skipped_tasks=skipped_tasks,
                execution_duration=execution_duration,
                error_summary=error_summary
            )

        except Exception as e:
            log_error("PlanningService.execute_plan", e, plan_id=request.plan_id)
            await self.plan_repo.update_plan_status(
                request.plan_id,
                PlanStatus.FAILED,
                0.0
            )
            raise

    # Goal Decomposition

    async def _decompose_goal(
        self,
        plan_id: UUID,
        goal: str,
        plan_data: dict[str, Any]
    ) -> list[TaskResponse]:
        """
        Decompose a goal into executable tasks.

        This is a simplified implementation. In production, this would
        use LLM-based decomposition or domain-specific planners.

        Args:
            plan_id: Parent plan ID
            goal: Goal to decompose
            plan_data: Plan configuration

        Returns:
            List of created tasks
        """
        tasks = []

        # Simple decomposition based on goal type
        # In production, this would be more sophisticated
        goal_lower = goal.lower()

        if "search" in goal_lower or "find" in goal_lower:
            # Search/retrieve type goal
            tasks.append(await self._create_task(
                plan_id,
                "Query Construction",
                "query",
                {"query": goal, "max_results": 10},
                TaskPriority.HIGH
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Execute Search",
                "search",
                {"use_cache": True},
                TaskPriority.HIGH
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Process Results",
                "process",
                {"format": "json"},
                TaskPriority.MEDIUM
            ))

        elif "create" in goal_lower or "generate" in goal_lower:
            # Creation type goal
            tasks.append(await self._create_task(
                plan_id,
                "Gather Requirements",
                "analyze",
                {"source": goal},
                TaskPriority.CRITICAL
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Draft Content",
                "generate",
                {"draft_only": True},
                TaskPriority.HIGH
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Review and Refine",
                "review",
                {"quality_threshold": 0.8},
                TaskPriority.MEDIUM
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Finalize Output",
                "finalize",
                {},
                TaskPriority.HIGH
            ))

        elif "analyze" in goal_lower or "process" in goal_lower:
            # Analysis type goal
            tasks.append(await self._create_task(
                plan_id,
                "Load Data",
                "load",
                {"source": "auto"},
                TaskPriority.HIGH
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Perform Analysis",
                "analyze",
                {"method": "auto"},
                TaskPriority.HIGH
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Generate Report",
                "report",
                {"format": "structured"},
                TaskPriority.MEDIUM
            ))

        else:
            # Generic decomposition
            tasks.append(await self._create_task(
                plan_id,
                "Understand Goal",
                "analyze",
                {"goal": goal},
                TaskPriority.CRITICAL
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Plan Approach",
                "plan",
                {},
                TaskPriority.HIGH
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Execute Plan",
                "execute",
                {},
                TaskPriority.HIGH
            ))
            tasks.append(await self._create_task(
                plan_id,
                "Verify Result",
                "verify",
                {},
                TaskPriority.MEDIUM
            ))

        return tasks

    async def _create_task(
        self,
        plan_id: UUID,
        title: str,
        task_type: str,
        parameters: dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> TaskResponse:
        """Helper to create a task."""
        task_data = TaskCreate(
            plan_id=plan_id,
            title=title,
            task_type=task_type,
            parameters=parameters,
            priority=priority
        )
        return await self.task_repo.create_task(task_data)

    async def _execute_tasks_parallel(
        self,
        tasks: list[TaskResponse],
        max_parallel: int,
        continue_on_failure: bool,
        error_summary: list[str]
    ) -> tuple[int, int, int]:
        """
        Execute tasks with limited parallelism.

        Args:
            tasks: Tasks to execute
            max_parallel: Maximum parallel tasks
            continue_on_failure: Continue on task failure
            error_summary: List to collect errors

        Returns:
            Tuple of (completed, failed, skipped) counts
        """
        completed = 0
        failed = 0
        skipped = 0

        # Create semaphore to limit parallelism
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_single_task(task: TaskResponse) -> tuple[bool, str | None]:
            """Execute a single task."""
            async with semaphore:
                try:
                    # Mark task as in progress
                    await self.task_repo.update_task(
                        task.task_id,
                        TaskStatus.IN_PROGRESS
                    )

                    # Simulate task execution (in production, this would call actual services)
                    await asyncio.sleep(0.1)  # Simulate work

                    # Mark task as completed
                    await self.task_repo.update_task(
                        task.task_id,
                        TaskStatus.COMPLETED,
                        result={"status": "success", "message": f"Task {task.title} completed"}
                    )

                    return True, None

                except Exception as e:
                    error_msg = f"Task {task.title} failed: {str(e)}"
                    error_summary.append(error_msg)

                    await self.task_repo.update_task(
                        task.task_id,
                        TaskStatus.FAILED,
                        error_message=str(e)
                    )

                    if not continue_on_failure:
                        raise

                    return False, str(e)

        # Process tasks in batches
        for task in tasks:
            try:
                success, error = await execute_single_task(task)
                if success:
                    completed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                if not continue_on_failure:
                    break
                # Count remaining as skipped
                remaining = len([t for t in tasks if t.task_id != task.task_id])
                skipped = remaining
                break

        return completed, failed, skipped

    async def _update_plan_progress(self, plan_id: UUID) -> None:
        """Update plan progress based on task completion."""
        plan = await self.plan_repo.get_plan(plan_id)
        if not plan:
            return

        if plan.task_count > 0:
            progress = plan.completed_tasks / plan.task_count
            await self.plan_repo.update_plan_status(
                plan_id,
                PlanStatus(plan.status),
                progress
            )

    # Replanning

    async def replan_on_failure(
        self,
        failed_plan_id: UUID,
        max_retries: int = 3
    ) -> PlanResponse | None:
        """
        Create a new plan after failure, learning from mistakes.

        Args:
            failed_plan_id: ID of failed plan
            max_retries: Maximum retry attempts

        Returns:
            New plan or None if retries exhausted
        """
        logger.info(f"Replanning for failed plan {failed_plan_id}")

        failed_plan = await self.plan_repo.get_plan(failed_plan_id)
        if not failed_plan:
            return None

        # Check retry count (stored in plan_data)
        retry_count = failed_plan.plan_data.get("retry_count", 0)

        if retry_count >= max_retries:
            logger.warning(f"Plan {failed_plan_id} exceeded max retries")
            return None

        # Get failed tasks for learning
        failed_tasks = await self.task_repo.get_plan_tasks(
            failed_plan_id,
            TaskStatus.FAILED
        )

        # Create new plan with learned adjustments
        new_plan_data = failed_plan.plan_data.copy()
        new_plan_data["retry_count"] = retry_count + 1
        new_plan_data["learned_from"] = str(failed_plan_id)
        new_plan_data["adjustments"] = self._generate_adjustments(failed_tasks)

        new_plan_create = PlanCreate(
            agent_id=failed_plan.agent_id,
            goal=failed_plan.goal + " (Retry)",
            plan_data=new_plan_data,
            parent_plan_id=failed_plan_id
        )

        return await self.create_plan(new_plan_create)

    def _generate_adjustments(self, failed_tasks: list[TaskResponse]) -> list[dict[str, Any]]:
        """Generate adjustments based on failed tasks."""
        adjustments = []

        for task in failed_tasks:
            if task.task_type == "search":
                adjustments.append({
                    "type": "search_params",
                    "adjustment": "increase_max_results",
                    "reason": f"Task {task.title} failed"
                })
            elif task.task_type == "generate":
                adjustments.append({
                    "type": "generation_params",
                    "adjustment": "increase_temperature",
                    "reason": f"Task {task.title} failed"
                })

        return adjustments

    # Plan History and Analytics

    async def get_plan_history(
        self,
        agent_id: str,
        from_plan: UUID | None = None,
        limit: int = 50
    ) -> list[PlanResponse]:
        """
        Get plan history for an agent.

        Args:
            agent_id: Agent ID
            from_plan: Starting plan (for pagination)
            limit: Max results

        Returns:
            List of plans
        """
        return await self.plan_repo.get_agent_plans(agent_id, limit=limit)
