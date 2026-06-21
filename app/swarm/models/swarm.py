"""
Swarm Model - Swarm configuration and state management
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SwarmType(str, Enum):
    """Types of swarms"""
    EVAL = "eval"
    RESEARCH = "research"
    SIMULATION = "simulation"
    LEARNING = "learning"
    MUTATION = "mutation"
    OPTIMIZATION = "optimization"
    RECURSIVE = "recursive"
    GOVERNANCE = "governance"


class SwarmState(str, Enum):
    """States a swarm can be in"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class SwarmDB(Base):
    """
    SQLAlchemy Swarm Model - Database representation.
    Tracks swarm lifecycle and state.
    """
    __tablename__ = "swarms"

    swarm_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    swarm_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="idle",
        index=True
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    agent_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=list
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
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


class SwarmConfig(BaseModel):
    """Swarm configuration parameters"""
    max_agents: int = Field(default=10, ge=1, le=100)
    task_queue_size: int = Field(default=100, ge=1, le=1000)
    coordination_pattern: str = Field(default="hierarchical", description="Coordination pattern: hierarchical, flat, hybrid")
    auto_scale: bool = Field(default=False, description="Auto-scale agents based on load")
    memory_scope: str = Field(default="swarm", description="Memory scope for this swarm")
    evaluation_interval: int = Field(default=300, ge=30, description="Evaluation interval in seconds")


class Swarm(BaseModel):
    """
    Pydantic Swarm Model - Business logic representation.
    """
    swarm_id: UUID = Field(default_factory=uuid4, description="Unique swarm identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Swarm name")
    swarm_type: SwarmType = Field(..., description="Type of swarm")
    state: SwarmState = Field(default=SwarmState.IDLE, description="Swarm state")
    config: SwarmConfig = Field(default_factory=SwarmConfig, description="Swarm configuration")
    agent_ids: list[UUID] = Field(default_factory=list, description="Agent IDs in this swarm")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    started_at: datetime | None = Field(default=None, description="When the swarm started")
    stopped_at: datetime | None = Field(default=None, description="When the swarm stopped")

    @field_validator('swarm_type')
    @classmethod
    def validate_swarm_type(cls, v):
        """Validate swarm type is in enum"""
        if isinstance(v, str):
            v = SwarmType(v)
        return v

    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        """Validate state is in enum"""
        if isinstance(v, str):
            v = SwarmState(v)
        return v


class SwarmCreate(BaseModel):
    """Swarm Creation Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Swarm name")
    swarm_type: SwarmType = Field(..., description="Type of swarm")
    config: SwarmConfig = Field(default_factory=SwarmConfig, description="Swarm configuration")
    initial_agent_count: int = Field(default=1, ge=0, le=50, description="Number of agents to create initially")


class SwarmUpdate(BaseModel):
    """Swarm Update Schema"""
    state: SwarmState | None = Field(default=None, description="New swarm state")
    config: SwarmConfig | None = Field(default=None, description="Updated configuration")


class SwarmResponse(BaseModel):
    """Swarm Response Schema"""
    swarm_id: UUID
    name: str
    swarm_type: str
    state: str
    config: dict[str, Any]
    agent_ids: list[UUID]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None


class SwarmStatus(BaseModel):
    """Detailed swarm status"""
    swarm_id: UUID
    name: str
    swarm_type: str
    state: str
    agent_count: int
    active_agents: int
    idle_agents: int
    error_agents: int
    tasks_pending: int
    tasks_in_progress: int
    tasks_completed: int
    tasks_failed: int
    uptime_seconds: int | None = None


class SwarmMetrics(BaseModel):
    """Swarm performance metrics"""
    swarm_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_tasks_processed: int
    avg_task_duration: float
    success_rate: float
    agent_utilization: float
    throughput_per_minute: float
