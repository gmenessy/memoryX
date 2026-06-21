"""
Loop Model - STUFE 0-6 orchestration and state management
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


class STUFEStage(str, Enum):
    """
    STUFE stages of the self-evolution loop.
    German for "Stage" - keeping the terminology from the specification.
    """
    STUFE_0 = "stufe_0"  # Recursive Awakening
    STUFE_1 = "stufe_1"  # Autonomous Self-Validation
    STUFE_2 = "stufe_2"  # Recursive Swarm Evaluation
    STUFE_3 = "stufe_3"  # Pattern Discovery & Consolidation
    STUFE_4 = "stufe_4"  # SOTA Research & Integration
    STUFE_5 = "stufe_5"  # Decision Optimization
    STUFE_6 = "stufe_6"  # Recursive Self-Programming


class LoopState(str, Enum):
    """States the loop can be in"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


class LoopDB(Base):
    """
    SQLAlchemy Loop Model - Database representation.
    Tracks the self-evolution loop state.
    """
    __tablename__ = "loops"

    loop_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    current_stufe: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="stufe_0"
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="idle"
    )
    cycle_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    active_swarm_ids: Mapped[list[UUID]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    auto_advance: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
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


class LoopConfig(BaseModel):
    """Loop configuration parameters"""
    auto_advance: bool = Field(default=True, description="Automatically advance through STUFEN")
    max_cycles: int | None = Field(default=None, ge=1, description="Maximum cycles before stopping")
    stufe_duration: dict[str, int] = Field(
        default_factory=lambda: {
            "stufe_0": 60,
            "stufe_1": 300,
            "stufe_2": 600,
            "stufe_3": 300,
            "stufe_4": 900,
            "stufe_5": 600,
            "stufe_6": 1200
        },
        description="Duration in seconds for each STUFE"
    )
    evaluation_interval: int = Field(default=60, ge=10, description="Evaluation interval in seconds")
    checkpoint_interval: int = Field(default=300, ge=60, description="Checkpoint interval in seconds")


class Loop(BaseModel):
    """
    Pydantic Loop Model - Business logic representation.
    """
    loop_id: UUID = Field(default_factory=uuid4, description="Unique loop identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Loop name")
    current_stufe: STUFEStage = Field(default=STUFEStage.STUFE_0, description="Current STUFE")
    state: LoopState = Field(default=LoopState.IDLE, description="Loop state")
    cycle_count: int = Field(default=0, ge=0, description="Number of completed cycles")
    active_swarm_ids: list[UUID] = Field(default_factory=list, description="Active swarm IDs")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Loop metrics")
    config: LoopConfig = Field(default_factory=LoopConfig, description="Loop configuration")
    auto_advance: bool = Field(default=True, description="Auto-advance through STUFEN")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    started_at: datetime | None = Field(default=None, description="When loop started")
    completed_at: datetime | None = Field(default=None, description="When loop completed")

    @field_validator('current_stufe')
    @classmethod
    def validate_current_stufe(cls, v):
        """Validate current_stufe is in enum"""
        if isinstance(v, str):
            v = STUFEStage(v)
        return v


class LoopCreate(BaseModel):
    """Loop Creation Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Loop name")
    config: LoopConfig = Field(default_factory=LoopConfig, description="Loop configuration")
    initial_swarm_ids: list[UUID] = Field(default_factory=list, description="Initial swarm IDs")


class LoopResponse(BaseModel):
    """Loop Response Schema"""
    loop_id: UUID
    name: str
    current_stufe: str
    state: str
    cycle_count: int
    active_swarm_ids: list[UUID]
    metrics: dict[str, Any]
    config: dict[str, Any]
    auto_advance: bool
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class STUFETransition(BaseModel):
    """STUFE transition event"""
    loop_id: UUID
    from_stufe: STUFEStage | None = None
    to_stufe: STUFEStage
    transition_time: datetime = Field(default_factory=datetime.utcnow)
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LoopMetrics(BaseModel):
    """Loop performance metrics"""
    loop_id: UUID
    cycle_count: int
    total_duration_seconds: int
    stufe_durations: dict[str, int]
    swarms_active: int
    tasks_processed: int
    mutations_created: int
    mutations_promoted: int
    self_programming_rate: float  # Percentage of prompts that were self-programmed
    overall_health_score: float


class SwarmStatusBoard(BaseModel):
    """
    Swarm Status Board - OUTPUT 1 from specification.
    Auto-scored board for deliverables.
    """
    deliverable_id: str
    deliverable_name: str
    auto_score: float  # 0.0-1.0
    value_impact: float  # 0.0-1.0
    quality_score: float  # 0.0-1.0
    safety_score: float  # 0.0-1.0
    prompt_health: str  # 🟢 v5.2, 🟡 v5.1, 🔴 v4.9, etc.
    decision: str  # AUTO-GO, CANARY, HOLD, BLOCK
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutiveSummary(BaseModel):
    """
    Executive Self-Programming Summary - OUTPUT 2 from specification.
    """
    loop_id: UUID
    cycle_number: int
    deployment_decision: str  # AUTO-GO, CANARY, HOLD
    value_delta: float
    intelligence_delta: float
    self_programming_rate: float  # Percentage of prompts that were mutated
    swarm_health: float  # 0.0-1.0
    autonomy_level: float  # 0.0-1.0, target: 95%+
    top_impediments: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class UltraScorecard(BaseModel):
    """
    Ultra Scorecard v5 - OUTPUT 3 from specification.
    """
    loop_id: UUID
    cycle_number: int
    feature_capability_status: str
    feature_capability_delta: str
    claude_code_quality_status: str
    claude_code_quality_delta: str
    integration_status: str
    integration_delta: str
    safety_alignment_status: str
    safety_alignment_delta: str
    user_value_status: str
    user_value_delta: str
    loop_self_evolution_status: str
    loop_self_evolution_delta: str
    recursive_self_programming_status: str
    recursive_self_programming_delta: str
    claude_confidence: float  # 0.0-1.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class BacklogItem(BaseModel):
    """
    Next Sprint Backlog Item - OUTPUT 4 from specification.
    """
    priority: str  # P0, P1, P2, P3
    experiment_name: str
    hypothesis: str
    expected_value: str
    complexity: str  # low, medium, high
    risk: str  # low, medium, high
    owner: str  # Which Claude agent/sub-swarm
    success_metric: str
    auto_run: bool
