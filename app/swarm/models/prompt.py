"""
Prompt Model - Prompt storage, versioning, and health tracking
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PromptType(str, Enum):
    """Types of prompts"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TEMPLATE = "template"


class PromptState(str, Enum):
    """States a prompt can be in"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PromptDB(Base):
    """
    SQLAlchemy Prompt Model - Database representation.
    Stores prompts with versioning and health tracking.
    """
    __tablename__ = "prompts"

    prompt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )
    content: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    prompt_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    purpose: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list
    )
    prompt_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",  # Column name remains 'metadata' in DB
        JSONB,
        nullable=False,
        default=dict
    )
    health_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    success_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    avg_response_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    parent_prompt_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft"
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
    last_evaluation: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class Prompt(BaseModel):
    """
    Pydantic Prompt Model - Business logic representation.
    """
    prompt_id: UUID = Field(default_factory=uuid4, description="Unique prompt identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    version: int = Field(default=1, ge=1, description="Prompt version")
    content: str = Field(..., min_length=1, description="Prompt content")
    prompt_type: PromptType = Field(..., description="Type of prompt")
    purpose: str = Field(..., min_length=1, max_length=500, description="Purpose of this prompt")
    tags: list[str] = Field(default_factory=list, description="Prompt tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    health_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Prompt health score")
    usage_count: int = Field(default=0, ge=0, description="Number of times used")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate")
    avg_response_time: float = Field(default=0.0, ge=0.0, description="Average response time in seconds")
    parent_prompt_id: UUID | None = Field(default=None, description="Parent prompt if mutated")
    is_active: bool = Field(default=False, description="Whether this is the active version")
    state: PromptState = Field(default=PromptState.DRAFT, description="Prompt state")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_evaluation: datetime = Field(default_factory=datetime.utcnow, description="Last health evaluation")

    @field_validator('prompt_type')
    @classmethod
    def validate_prompt_type(cls, v):
        """Validate prompt type is in enum"""
        if isinstance(v, str):
            v = PromptType(v)
        return v


class PromptCreate(BaseModel):
    """Prompt Creation Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    content: str = Field(..., min_length=1, description="Prompt content")
    prompt_type: PromptType = Field(..., description="Type of prompt")
    purpose: str = Field(..., min_length=1, max_length=500, description="Purpose of this prompt")
    tags: list[str] = Field(default_factory=list, description="Prompt tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PromptUpdate(BaseModel):
    """Prompt Update Schema"""
    content: str | None = Field(default=None, description="Updated prompt content")
    purpose: str | None = Field(default=None, description="Updated purpose")
    tags: list[str] | None = Field(default=None, description="Updated tags")
    metadata: dict[str, Any] | None = Field(default=None, description="Updated metadata")


class PromptResponse(BaseModel):
    """Prompt Response Schema"""
    prompt_id: UUID
    name: str
    version: int
    content: str
    prompt_type: str
    purpose: str
    tags: list[str]
    metadata: dict[str, Any]
    health_score: float
    usage_count: int
    success_rate: float
    avg_response_time: float
    parent_prompt_id: UUID | None
    is_active: bool
    state: str
    created_at: datetime
    updated_at: datetime
    last_evaluation: datetime


class PromptHealth(BaseModel):
    """Prompt health update data"""
    prompt_id: UUID
    success: bool
    response_time: float = Field(..., ge=0.0, description="Response time in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional health metadata")


class PromptUsageRecord(BaseModel):
    """Record of prompt usage"""
    prompt_id: UUID
    agent_id: UUID
    task_id: UUID | None = None
    success: bool
    response_time: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PromptSearchParams(BaseModel):
    """Prompt search parameters"""
    query: str | None = None
    prompt_type: PromptType | None = None
    tags: list[str] | None = None
    min_health_score: float | None = None
    is_active: bool | None = None
    limit: int = Field(default=50, ge=1, le=200)
