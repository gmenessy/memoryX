"""
Event Model - Append-only Truth Layer
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, JSON, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EventDB(Base):
    """
    SQLAlchemy Event Model - Database representation.
    Implements append-only truth layer (no deletion, no overwriting).
    """
    __tablename__ = "events"

    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True  # Add index for time-based queries
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    actor: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",  # Column name remains 'metadata' in DB
        JSON,
        nullable=False,
        default={}
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_event_scope_type', 'scope', 'event_type'),
        Index('idx_event_actor_type', 'actor', 'event_type'),
        Index('idx_event_timestamp_scope', 'timestamp', 'scope'),
    )


class Event(BaseModel):
    """
    Pydantic Event Model - API representation.
    Immutable by design to prevent accidental modifications.
    """
    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    event_type: str = Field(..., description="Type of event (e.g., user_input, agent_action, tool_call)")
    actor: str = Field(..., description="Who triggered the event (user ID, agent ID, system)")
    scope: str = Field(..., description="Scope/context of the event (case_id, session_id, global)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"frozen": True}  # Make immutable


class EventCreate(BaseModel):
    """
    Event Creation Schema - Input for creating new events.
    """
    event_type: str = Field(..., description="Type of event")
    actor: str = Field(..., description="Who triggered the event")
    scope: str = Field(..., description="Scope/context of the event")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EventResponse(BaseModel):
    """
    Event Response Schema - API response format.
    """
    event_id: UUID
    timestamp: datetime
    event_type: str
    actor: str
    scope: str
    payload: dict[str, Any]
    metadata: dict[str, Any]


# Event Types as per specification
EVENT_TYPES = [
    "user_input",
    "agent_action",
    "tool_call",
    "decision",
    "memory_update",
    "correction",
    "failure",
    "success",
    "policy_violation",
    "risk_event"
]