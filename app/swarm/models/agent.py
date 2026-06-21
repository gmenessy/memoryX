"""
Agent Model - Agent lifecycle, state, and types
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentType(str, Enum):
    """Types of agents in the swarm system"""
    BASE = "base"
    EVAL = "eval"
    RESEARCH = "research"
    SIMULATION = "simulation"
    LEARNING = "learning"
    MUTATION = "mutation"
    OPTIMIZATION = "optimization"
    RECURSIVE = "recursive"


class AgentState(str, Enum):
    """States an agent can be in"""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"


class AgentDB(Base):
    """
    SQLAlchemy Agent Model - Database representation.
    Tracks agent lifecycle and state.
    """
    __tablename__ = "agents"

    agent_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    agent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="idle",
        index=True
    )
    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    current_task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True
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
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class AgentConfig(BaseModel):
    """Agent configuration parameters"""
    max_concurrent_tasks: int = Field(default=1, ge=1, le=10)
    heartbeat_interval: int = Field(default=30, ge=5, le=300)
    task_timeout: int = Field(default=300, ge=30, le=3600)
    retry_limit: int = Field(default=3, ge=0, le=10)
    memory_scope: str = Field(default="global")


class Agent(BaseModel):
    """
    Pydantic Agent Model - Business logic representation.
    """
    agent_id: UUID = Field(default_factory=uuid4, description="Unique agent identifier")
    agent_type: AgentType = Field(..., description="Type of agent")
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    state: AgentState = Field(default=AgentState.IDLE, description="Agent state")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    config: AgentConfig = Field(default_factory=AgentConfig, description="Agent configuration")
    current_task_id: UUID | None = Field(default=None, description="Current assigned task")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow, description="Last heartbeat")

    @field_validator('agent_type')
    @classmethod
    def validate_agent_type(cls, v):
        """Validate agent type is in enum"""
        if isinstance(v, str):
            v = AgentType(v)
        return v

    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        """Validate state is in enum"""
        if isinstance(v, str):
            v = AgentState(v)
        return v


class AgentCreate(BaseModel):
    """Agent Creation Schema"""
    agent_type: AgentType = Field(..., description="Type of agent to create")
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    config: AgentConfig = Field(default_factory=AgentConfig, description="Agent configuration")


class AgentUpdate(BaseModel):
    """Agent Update Schema"""
    state: AgentState | None = Field(default=None, description="New agent state")
    capabilities: list[str] | None = Field(default=None, description="Updated capabilities")
    config: AgentConfig | None = Field(default=None, description="Updated configuration")


class AgentResponse(BaseModel):
    """Agent Response Schema"""
    agent_id: UUID
    agent_type: str
    name: str
    state: str
    capabilities: list[str]
    config: dict[str, Any]
    current_task_id: UUID | None
    created_at: datetime
    updated_at: datetime
    last_heartbeat: datetime


class AgentHeartbeat(BaseModel):
    """Agent heartbeat data"""
    agent_id: UUID
    state: AgentState
    current_task_id: UUID | None = None
    metrics: dict[str, Any] = Field(default_factory=dict, description="Agent performance metrics")


class AgentMetrics(BaseModel):
    """Agent performance metrics"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_task_duration: float = 0.0
    success_rate: float = 0.0
    last_error: str | None = None
