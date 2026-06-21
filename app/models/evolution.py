"""
Evolution Memory Model - Memory Evolution System
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MemoryPatchDB(Base):
    """
    SQLAlchemy Memory Patch Model - Database representation.
    Tracks how memory evolves over time without deletion.
    """
    __tablename__ = "memory_patches"

    patch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    target_memory: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True
    )
    patch_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    old_value: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    new_value: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class MemoryPatch(BaseModel):
    """
    Pydantic Memory Patch Model - API representation.
    """
    patch_id: UUID = Field(default_factory=uuid4, description="Unique patch identifier")
    target_memory: UUID = Field(..., description="Target memory ID to patch")
    patch_type: str = Field(..., description="Type of patch (update, merge, split, deprecate, archive, promotion)")
    old_value: dict[str, Any] = Field(default_factory=dict, description="Previous value/state")
    new_value: dict[str, Any] = Field(default_factory=dict, description="New value/state")
    reason: str = Field(..., description="Reason for the patch", min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this patch")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @validator('patch_type')
    def validate_patch_type(cls, v):
        """Validate patch type is one of the allowed types."""
        allowed_types = [
            "update",      # Direct update of memory content
            "merge",       # Merge multiple memories
            "split",       # Split memory into multiple parts
            "deprecate",   # Mark memory as deprecated
            "archive",     # Archive memory
            "promotion"    # Promote memory (e.g., from candidate to active)
        ]
        if v not in allowed_types:
            raise ValueError(f"Invalid patch_type: {v}. Must be one of: {', '.join(allowed_types)}")
        return v

    @validator('reason')
    def validate_reason(cls, v):
        """Validate reason is not empty."""
        if not v.strip():
            raise ValueError("Reason cannot be empty")
        return v.strip()


class MemoryPatchCreate(BaseModel):
    """
    Memory Patch Creation Schema.
    """
    target_memory: UUID = Field(..., description="Target memory ID")
    patch_type: str = Field(..., description="Type of patch")
    old_value: dict[str, Any] = Field(default_factory=dict, description="Previous value")
    new_value: dict[str, Any] = Field(default_factory=dict, description="New value")
    reason: str = Field(..., description="Reason for the patch", min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score")


class MemoryPatchResponse(BaseModel):
    """
    Memory Patch Response Schema.
    """
    patch_id: UUID
    target_memory: UUID
    patch_type: str
    old_value: dict[str, Any]
    new_value: dict[str, Any]
    reason: str
    confidence: float
    created_at: datetime


class MemoryEvolutionHistory(BaseModel):
    """
    Memory Evolution History Response.
    Shows the complete evolution history of a memory.
    """
    memory_id: UUID
    total_patches: int
    patches: list[MemoryPatchResponse]
    current_state: dict[str, Any]
    fitness_score: float


# Patch Types as per specification
PATCH_TYPES = [
    "update",      # Direct update of memory content
    "merge",       # Merge multiple memories
    "split",       # Split memory into multiple parts
    "deprecate",   # Mark memory as deprecated
    "archive",     # Archive memory
    "promotion"    # Promote memory (e.g., from candidate to active)
]

# Memory States as per specification
MEMORY_STATES = [
    "candidate",   # Newly created, not yet validated
    "active",      # Active and in use
    "evolving",    # Currently being refined
    "deprecated",  # Deprecated but kept for reference
    "archived"     # Archived and rarely accessed
]