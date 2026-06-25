"""
Planning Models - Decision Making and Goal Decomposition
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Float, JSON, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlanStatus(str, Enum):
    """Status of a plan."""
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Status of a task within a plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlanDB(Base):
    """
    SQLAlchemy Plan Model - Database representation.
    Stores agent plans with goals and tasks.
    """
    __tablename__ = "plans"

    plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    agent_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    goal: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    plan_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        index=True
    )
    progress: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    parent_plan_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


class TaskDB(Base):
    """
    SQLAlchemy Task Model - Database representation.
    Stores tasks within plans.
    """
    __tablename__ = "plan_tasks"

    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True
    )
    parent_task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    task_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="medium"
    )
    estimated_duration: Mapped[int | None] = mapped_column(
        Float,
        nullable=True
    )
    actual_duration: Mapped[int | None] = mapped_column(
        Float,
        nullable=True
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


# Pydantic Models

class Plan(BaseModel):
    """Pydantic Plan Model - API representation."""
    plan_id: UUID = Field(default_factory=uuid4, description="Unique plan identifier")
    agent_id: str = Field(..., description="Agent ID creating this plan")
    goal: str = Field(..., description="High-level goal to achieve")
    plan_data: dict[str, Any] = Field(default_factory=dict, description="Plan configuration and metadata")
    status: PlanStatus = Field(default=PlanStatus.DRAFT, description="Plan status")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress percentage (0-1)")
    parent_plan_id: UUID | None = Field(None, description="Parent plan if sub-plan")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")

    @field_validator('goal')
    @classmethod
    def validate_goal(cls, v: str) -> str:
        """Validate goal is not empty."""
        if not v.strip():
            raise ValueError("Goal cannot be empty")
        return v.strip()


class PlanCreate(BaseModel):
    """Plan Creation Schema."""
    agent_id: str = Field(..., description="Agent ID")
    goal: str = Field(..., description="Goal to achieve")
    plan_data: dict[str, Any] = Field(default_factory=dict, description="Plan configuration")
    parent_plan_id: UUID | None = Field(None, description="Parent plan if sub-plan")


class PlanUpdate(BaseModel):
    """Plan Update Schema."""
    status: PlanStatus | None = Field(None, description="Plan status")
    progress: float | None = Field(None, ge=0.0, le=1.0, description="Progress update")
    plan_data: dict[str, Any] | None = Field(None, description="Plan data update")


class Task(BaseModel):
    """Pydantic Task Model - API representation."""
    task_id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    plan_id: UUID = Field(..., description="Parent plan ID")
    parent_task_id: UUID | None = Field(None, description="Parent task if sub-task")
    title: str = Field(..., description="Task title", min_length=1, max_length=500)
    description: str | None = Field(None, description="Task description")
    task_type: str = Field(..., description="Type of task")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    estimated_duration: float | None = Field(None, ge=0.0, description="Estimated duration in seconds")
    actual_duration: float | None = Field(None, ge=0.0, description="Actual duration in seconds")
    result: dict[str, Any] | None = Field(None, description="Task execution result")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: datetime | None = Field(None, description="Task start timestamp")
    completed_at: datetime | None = Field(None, description="Task completion timestamp")


class TaskCreate(BaseModel):
    """Task Creation Schema."""
    plan_id: UUID = Field(..., description="Parent plan ID")
    parent_task_id: UUID | None = Field(None, description="Parent task if sub-task")
    title: str = Field(..., description="Task title", min_length=1, max_length=500)
    description: str | None = Field(None, description="Task description")
    task_type: str = Field(..., description="Type of task")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    estimated_duration: float | None = Field(None, ge=0.0, description="Estimated duration")


class TaskUpdate(BaseModel):
    """Task Update Schema."""
    status: TaskStatus | None = Field(None, description="Task status")
    result: dict[str, Any] | None = Field(None, description="Task result")
    error_message: str | None = Field(None, description="Error message")


class PlanResponse(BaseModel):
    """Plan Response with tasks."""
    plan_id: UUID
    agent_id: str
    goal: str
    plan_data: dict[str, Any]
    status: PlanStatus
    progress: float
    parent_plan_id: UUID | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    task_count: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


class TaskResponse(BaseModel):
    """Task Response Schema."""
    task_id: UUID
    plan_id: UUID
    parent_task_id: UUID | None
    title: str
    description: str | None
    task_type: str
    parameters: dict[str, Any]
    status: TaskStatus
    priority: TaskPriority
    estimated_duration: float | None
    actual_duration: float | None
    result: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class PlanExecutionRequest(BaseModel):
    """Request to execute a plan."""
    plan_id: UUID = Field(..., description="Plan to execute")
    max_parallel_tasks: int = Field(default=3, ge=1, le=10, description="Max parallel tasks")
    continue_on_failure: bool = Field(default=False, description="Continue on task failure")


class PlanExecutionResult(BaseModel):
    """Result of plan execution."""
    plan_id: UUID
    status: PlanStatus
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    execution_duration: float
    error_summary: list[str] = Field(default_factory=list)


# Constants for easy reference
PLAN_STATUSES = [status.value for status in PlanStatus]
TASK_STATUSES = [status.value for status in TaskStatus]
TASK_PRIORITIES = [priority.value for priority in TaskPriority]
