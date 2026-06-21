"""
Mutation Model - Prompt mutation operations and A/B testing
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, Float, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MutationType(str, Enum):
    """Types of prompt mutations"""
    REFACTOR = "refactor"
    EXTEND = "extend"
    SIMPLIFY = "simplify"
    RESTRUCTURE = "restructure"
    OPTIMIZE = "optimize"
    CLARIFY = "clarify"
    SPECIALIZE = "specialize"
    GENERALIZE = "generalize"
    HYBRID = "hybrid"
    RADICAL = "radical"


class MutationState(str, Enum):
    """States a mutation can be in"""
    DRAFT = "draft"
    TESTING = "testing"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


class MutationDB(Base):
    """
    SQLAlchemy Mutation Model - Database representation.
    Tracks prompt mutations and A/B tests.
    """
    __tablename__ = "mutations"

    mutation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    source_prompt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True
    )
    target_prompt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True
    )
    mutation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    description: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft"
    )
    ab_test_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    ab_test_results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
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
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


class Mutation(BaseModel):
    """
    Pydantic Mutation Model - Business logic representation.
    """
    mutation_id: UUID = Field(default_factory=uuid4, description="Unique mutation identifier")
    source_prompt_id: UUID = Field(..., description="Source prompt being mutated")
    target_prompt_id: UUID = Field(..., description="New mutated prompt")
    mutation_type: MutationType = Field(..., description="Type of mutation")
    description: str = Field(..., min_length=1, description="Description of mutation")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this mutation")
    state: MutationState = Field(default=MutationState.DRAFT, description="Mutation state")
    ab_test_active: bool = Field(default=False, description="Whether A/B test is active")
    ab_test_results: dict[str, Any] | None = Field(default=None, description="A/B test results")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    deployed_at: datetime | None = Field(default=None, description="Deployment timestamp")

    @field_validator('mutation_type')
    @classmethod
    def validate_mutation_type(cls, v):
        """Validate mutation type is in enum"""
        if isinstance(v, str):
            v = MutationType(v)
        return v


class MutationCreate(BaseModel):
    """Mutation Creation Schema"""
    source_prompt_id: UUID = Field(..., description="Source prompt to mutate")
    mutation_type: MutationType = Field(..., description="Type of mutation")
    description: str = Field(..., min_length=1, description="Description of mutation")
    target_content: str = Field(..., min_length=1, description="Content of mutated prompt")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this mutation")


class MutationResponse(BaseModel):
    """Mutation Response Schema"""
    mutation_id: UUID
    source_prompt_id: UUID
    target_prompt_id: UUID
    mutation_type: str
    description: str
    confidence: float
    state: str
    ab_test_active: bool
    ab_test_results: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    deployed_at: datetime | None


class ABTestConfig(BaseModel):
    """A/B test configuration"""
    mutation_id: UUID
    sample_size: int = Field(default=100, ge=10, description="Sample size for A/B test")
    traffic_split: float = Field(default=0.5, ge=0.1, le=0.9, description="Traffic split for variant (0-1)")
    duration_hours: int = Field(default=24, ge=1, description="Test duration in hours")
    metrics: list[str] = Field(default_factory=list, description="Metrics to evaluate")


class ABTestResult(BaseModel):
    """A/B test result data"""
    variant: str = Field(..., description="Variant identifier (control or treatment)")
    sample_size: int
    success_count: int
    failure_count: int
    avg_response_time: float
    avg_quality_score: float
    error_rate: float


class MutationEvaluation(BaseModel):
    """Mutation evaluation results"""
    mutation_id: UUID
    should_promote: bool
    confidence: float
    reason: str
    metrics: dict[str, Any]
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class MutationSearchParams(BaseModel):
    """Mutation search parameters"""
    source_prompt_id: UUID | None = None
    mutation_type: MutationType | None = None
    state: MutationState | None = None
    ab_test_active: bool | None = None
    limit: int = Field(default=50, ge=1, le=200)
