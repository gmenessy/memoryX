"""
Memory Card Model - Typed Information Storage
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Float, JSON, String, Text, Index
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MemoryCardDB(Base):
    """
    SQLAlchemy Memory Card Model - Database representation.
    Stores all information as typed memory cards.
    """
    __tablename__ = "memory_cards"

    memory_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        index=True  # Add index for confidence range queries
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    source_events: Mapped[list[UUID]] = mapped_column(
        JSON,  # SQLite doesn't support ARRAY, use JSON instead
        nullable=False,
        default=[]
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True  # Add index for time-based sorting/filtering
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_memory_scope_type', 'scope', 'memory_type'),
        Index('idx_memory_scope_confidence', 'scope', 'confidence'),
        Index('idx_memory_created_scope', 'created_at', 'scope'),
    )


class MemoryCard(BaseModel):
    """
    Pydantic Memory Card Model - API representation.
    """
    memory_id: UUID = Field(default_factory=uuid4, description="Unique memory identifier")
    memory_type: str = Field(..., description="Type of memory (episodic, semantic, procedural, etc.)")
    title: str = Field(..., description="Memory title", min_length=1, max_length=500)
    content: str = Field(..., description="Memory content", min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score (0-1)")
    scope: str = Field(..., description="Scope/context (case_id, session_id, global)")
    source_events: list[UUID] = Field(default_factory=list, description="Source event IDs")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @field_validator('memory_type')
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        """Validate memory type is one of the allowed types."""
        allowed_types = [
            "episodic",
            "semantic",
            "procedural",
            "preference",
            "governance",
            "risk",
            "skill",
            "decision"
        ]
        if v not in allowed_types:
            raise ValueError(f"Invalid memory_type: {v}. Must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()


class MemoryCardCreate(BaseModel):
    """
    Memory Card Creation Schema.
    """
    memory_type: str = Field(..., description="Type of memory")
    title: str = Field(..., description="Memory title", min_length=1, max_length=500)
    content: str = Field(..., description="Memory content", min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score")
    scope: str = Field(..., description="Scope/context")
    source_events: list[UUID] = Field(default_factory=list, description="Source event IDs")


class MemoryCardUpdate(BaseModel):
    """
    Memory Card Update Schema - partial update support.
    """
    title: str | None = Field(None, description="Memory title", min_length=1, max_length=500)
    content: str | None = Field(None, description="Memory content", min_length=1)
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Confidence score")
    scope: str | None = Field(None, description="Scope/context")


class MemoryCardResponse(BaseModel):
    """
    Memory Card Response Schema.
    """
    memory_id: UUID
    memory_type: str
    title: str
    content: str
    confidence: float
    scope: str
    source_events: list[UUID]
    created_at: datetime
    updated_at: datetime


# Memory Types as per specification
MEMORY_TYPES = [
    "episodic",      # Specific experiences and events
    "semantic",      # General knowledge and facts
    "procedural",     # How-to knowledge and skills
    "preference",    # User preferences and settings
    "governance",    # Rules and policies
    "risk",          # Risk assessments and warnings
    "skill",         # Learned skills and capabilities
    "decision"       # Decisions made with reasoning
]