"""
Task Model - Task distribution and tracking
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskType(str, Enum):
    """Types of tasks"""
    EVALUATION = "evaluation"
    RESEARCH = "research"
    SIMULATION = "simulation"
    LEARNING = "learning"
    MUTATION = "mutation"
    OPTIMIZATION = "optimization"
    SELF_PROGRAMMING = "self_programming"
    COORDINATION = "coordination"
    GENERAL = "general"


class TaskState(str, Enum):
    """States a task can be in"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskDB(Base):
    """
    SQLAlchemy Task Model - Database representation.
    Tracks task lifecycle and distribution.
    """
    __tablename__ = "tasks"

    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    swarm_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True
    )
    assigned_agent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
    error: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3
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
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    timeout_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


class Task(BaseModel):
    """
    Pydantic Task Model - Business logic representation.
    """
    task_id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    swarm_id: UUID = Field(..., description="Swarm ID this task belongs to")
    assigned_agent_id: UUID | None = Field(default=None, description="Agent assigned to this task")
    task_type: TaskType = Field(..., description="Type of task")
    payload: dict[str, Any] = Field(default_factory=dict, description="Task payload/data")
    state: TaskState = Field(default=TaskState.PENDING, description="Task state")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    result: dict[str, Any] | None = Field(default=None, description="Task result")
    error: str | None = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retries")
    max_retries: int = Field(default=3, ge=0, description="Maximum retries allowed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    started_at: datetime | None = Field(default=None, description="When task started")
    completed_at: datetime | None = Field(default=None, description="When task completed")
    timeout_at: datetime | None = Field(default=None, description="Task timeout timestamp")

    @field_validator('task_type')
    @classmethod
    def validate_task_type(cls, v):
        """Validate task type is in enum"""
        if isinstance(v, str):
            v = TaskType(v)
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        """Convert priority to integer value"""
        if isinstance(v, TaskPriority):
            priority_map = {
                TaskPriority.LOW: 1,
                TaskPriority.MEDIUM: 5,
                TaskPriority.HIGH: 8,
                TaskPriority.CRITICAL: 10
            }
            return priority_map[v]
        return v


class TaskCreate(BaseModel):
    """Task Creation Schema"""
    swarm_id: UUID = Field(..., description="Swarm ID")
    task_type: TaskType = Field(..., description="Type of task")
    payload: dict[str, Any] = Field(default_factory=dict, description="Task payload")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    timeout_seconds: int = Field(default=300, ge=10, description="Task timeout in seconds")


class TaskUpdate(BaseModel):
    """Task Update Schema"""
    state: TaskState | None = Field(default=None, description="New task state")
    result: dict[str, Any] | None = Field(default=None, description="Task result")
    error: str | None = Field(default=None, description="Error message")


class TaskResponse(BaseModel):
    """Task Response Schema"""
    task_id: UUID
    swarm_id: UUID
    assigned_agent_id: UUID | None
    task_type: str
    payload: dict[str, Any]
    state: str
    priority: int
    result: dict[str, Any] | None
    error: str | None
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    timeout_at: datetime | None


class TaskAssignment(BaseModel):
    """Task assignment data"""
    task_id: UUID
    agent_id: UUID
    assigned_at: datetime = Field(default_factory=datetime.utcnow)


class TaskResult(BaseModel):
    """Task completion result"""
    task_id: UUID
    agent_id: UUID
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_seconds: float
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class TaskSearchParams(BaseModel):
    """Task search parameters"""
    swarm_id: UUID | None = None
    assigned_agent_id: UUID | None = None
    task_type: TaskType | None = None
    state: TaskState | None = None
    priority: TaskPriority | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
