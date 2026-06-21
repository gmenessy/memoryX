"""
Dream Engine Models - Async Consolidation System

The Dream Engine provides asynchronous memory consolidation:
- Daydream: Event → Memory Transformation (running)
- Nightdream: Merge, Compress, Deduplicate (periodic)
- Deepdream: Pattern Discovery, Policy Discovery (strategic)
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Float, JSON, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DreamType(str, Enum):
    """Types of dream operations."""
    DAYDREAM = "daydream"   # Event → Memory transformation
    NIGHTDREAM = "nightdream"  # Merge, Compress, Deduplicate
    DEEPDREAM = "deepdream"    # Pattern Discovery, Policy Discovery


class DreamStatus(str, Enum):
    """Status of dream operations."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransformationType(str, Enum):
    """Types of event-to-memory transformations."""
    DIRECT = "direct"           # Direct event to memory
    AGGREGATED = "aggregated"   # Multiple events to single memory
    EXTRACTED = "extracted"     # Extract key information
    INFERRED = "inferred"       # Infer new knowledge


class DaydreamJobDB(Base):
    """
    SQLAlchemy Daydream Job Model - Database representation.
    Tracks Event → Memory transformation jobs.
    """
    __tablename__ = "daydream_jobs"

    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    dream_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DreamType.DAYDREAM.value
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DreamStatus.PENDING.value
    )
    transformation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TransformationType.DIRECT.value
    )
    source_events: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=[]
    )
    target_memory: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True
    )
    processing_params: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    priority: Mapped[int] = mapped_column(
        Float,
        nullable=False,
        default=0.5
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class NightdreamJobDB(Base):
    """
    SQLAlchemy Nightdream Job Model - Database representation.
    Tracks periodic consolidation jobs (merge, compress, deduplicate).
    """
    __tablename__ = "nightdream_jobs"

    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    dream_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DreamType.NIGHTDREAM.value
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DreamStatus.PENDING.value
    )
    operation: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # merge, compress, deduplicate
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    target_memories: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=[]
    )
    result_memories: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=[]
    )
    processing_params: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class DeepdreamJobDB(Base):
    """
    SQLAlchemy Deepdream Job Model - Database representation.
    Tracks strategic pattern discovery jobs.
    """
    __tablename__ = "deepdream_jobs"

    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    dream_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DreamType.DEEPDREAM.value
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DreamStatus.PENDING.value
    )
    operation: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # pattern_discovery, policy_discovery, dna_evolution
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    analysis_depth: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="standard"
    )  # quick, standard, deep
    processing_params: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    patterns_found: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
    policies_suggested: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=[]
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# Pydantic Models for API


class DaydreamJob(BaseModel):
    """Pydantic Daydream Job Model - API representation."""
    job_id: UUID = Field(default_factory=uuid4, description="Unique job identifier")
    dream_type: str = Field(default=DreamType.DAYDREAM.value, description="Type of dream")
    status: str = Field(default=DreamStatus.PENDING.value, description="Job status")
    transformation_type: str = Field(default=TransformationType.DIRECT.value, description="Transformation type")
    source_events: list[UUID] = Field(default_factory=list, description="Source event IDs")
    target_memory: UUID | None = Field(None, description="Created memory ID")
    processing_params: dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    result: dict[str, Any] | None = Field(None, description="Job result")
    error_message: str | None = Field(None, description="Error message if failed")
    priority: float = Field(default=0.5, ge=0.0, le=1.0, description="Job priority")
    started_at: datetime | None = Field(None, description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")

    @field_validator('dream_type')
    def validate_dream_type(cls, v):
        allowed = [dt.value for dt in DreamType]
        if v not in allowed:
            raise ValueError(f"Invalid dream_type: {v}")
        return v

    @field_validator('status')
    def validate_status(cls, v):
        allowed = [ds.value for ds in DreamStatus]
        if v not in allowed:
            raise ValueError(f"Invalid status: {v}")
        return v

    @field_validator('transformation_type')
    def validate_transformation_type(cls, v):
        allowed = [tt.value for tt in TransformationType]
        if v not in allowed:
            raise ValueError(f"Invalid transformation_type: {v}")
        return v


class DaydreamJobCreate(BaseModel):
    """Daydream Job Creation Schema."""
    source_events: list[UUID] = Field(..., description="Source event IDs", min_items=1)
    transformation_type: str = Field(default=TransformationType.DIRECT.value, description="Transformation type")
    processing_params: dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    priority: float = Field(default=0.5, ge=0.0, le=1.0, description="Job priority")


class DaydreamJobResponse(BaseModel):
    """Daydream Job Response Schema."""
    job_id: UUID
    dream_type: str
    status: str
    transformation_type: str
    source_events: list[UUID]
    target_memory: UUID | None
    processing_params: dict[str, Any]
    result: dict[str, Any] | None
    error_message: str | None
    priority: float
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class NightdreamJob(BaseModel):
    """Pydantic Nightdream Job Model - API representation."""
    job_id: UUID = Field(default_factory=uuid4, description="Unique job identifier")
    dream_type: str = Field(default=DreamType.NIGHTDREAM.value, description="Type of dream")
    status: str = Field(default=DreamStatus.PENDING.value, description="Job status")
    operation: str = Field(..., description="Operation (merge, compress, deduplicate)")
    scope: str = Field(..., description="Operation scope")
    target_memories: list[UUID] = Field(default_factory=list, description="Target memory IDs")
    result_memories: list[UUID] = Field(default_factory=list, description="Result memory IDs")
    processing_params: dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    result: dict[str, Any] | None = Field(None, description="Job result")
    error_message: str | None = Field(None, description="Error message if failed")
    scheduled_for: datetime | None = Field(None, description="Scheduled execution time")
    started_at: datetime | None = Field(None, description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class NightdreamJobCreate(BaseModel):
    """Nightdream Job Creation Schema."""
    operation: str = Field(..., description="Operation (merge, compress, deduplicate)")
    scope: str = Field(..., description="Operation scope")
    target_memories: list[UUID] = Field(default_factory=list, description="Target memory IDs")
    processing_params: dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    scheduled_for: datetime | None = Field(None, description="Schedule for specific time")


class NightdreamJobResponse(BaseModel):
    """Nightdream Job Response Schema."""
    job_id: UUID
    dream_type: str
    status: str
    operation: str
    scope: str
    target_memories: list[UUID]
    result_memories: list[UUID]
    processing_params: dict[str, Any]
    result: dict[str, Any] | None
    error_message: str | None
    scheduled_for: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DeepdreamJob(BaseModel):
    """Pydantic Deepdream Job Model - API representation."""
    job_id: UUID = Field(default_factory=uuid4, description="Unique job identifier")
    dream_type: str = Field(default=DreamType.DEEPDREAM.value, description="Type of dream")
    status: str = Field(default=DreamStatus.PENDING.value, description="Job status")
    operation: str = Field(..., description="Operation (pattern_discovery, policy_discovery, dna_evolution)")
    scope: str = Field(..., description="Analysis scope")
    analysis_depth: str = Field(default="standard", description="Analysis depth (quick, standard, deep)")
    processing_params: dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    patterns_found: dict[str, Any] | None = Field(None, description="Discovered patterns")
    policies_suggested: list[dict[str, Any]] = Field(default_factory=list, description="Suggested policies")
    result: dict[str, Any] | None = Field(None, description="Job result")
    error_message: str | None = Field(None, description="Error message if failed")
    started_at: datetime | None = Field(None, description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class DeepdreamJobCreate(BaseModel):
    """Deepdream Job Creation Schema."""
    operation: str = Field(..., description="Operation")
    scope: str = Field(..., description="Analysis scope")
    analysis_depth: str = Field(default="standard", description="Analysis depth")
    processing_params: dict[str, Any] = Field(default_factory=dict, description="Processing parameters")


class DeepdreamJobResponse(BaseModel):
    """Deepdream Job Response Schema."""
    job_id: UUID
    dream_type: str
    status: str
    operation: str
    scope: str
    analysis_depth: str
    processing_params: dict[str, Any]
    patterns_found: dict[str, Any] | None
    policies_suggested: list[dict[str, Any]]
    result: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# Constants

DREAM_TYPES = [dt.value for dt in DreamType]
DREAM_STATUSES = [ds.value for ds in DreamStatus]
TRANSFORMATION_TYPES = [tt.value for tt in TransformationType]
NIGHTDREAM_OPERATIONS = ["merge", "compress", "deduplicate"]
DEEPDREAM_OPERATIONS = ["pattern_discovery", "policy_discovery", "dna_evolution"]
ANALYSIS_DEPTHS = ["quick", "standard", "deep"]
