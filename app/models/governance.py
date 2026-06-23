"""
Governance Models - Memory Gatekeeper and Governance Rules
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator
from sqlalchemy import DateTime, Float, JSON, String, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Action(str, Enum):
    """Possible actions for governance rules."""
    ALLOW = "allow"
    WARN = "warn"
    REVIEW = "review"
    BLOCK = "block"
    ALTERNATIVE = "alternative"


class Severity(str, Enum):
    """Severity levels for governance rules."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GovernanceRuleDB(Base):
    """
    SQLAlchemy Governance Rule Model - Database representation.
    Stores executable governance rules for memory operations.
    """
    __tablename__ = "governance_rules"

    rule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    condition: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="medium",
        index=True  # Add index for severity filtering
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True  # Add index for scope filtering
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True  # Add index for enabled filtering
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

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_governance_scope_enabled', 'scope', 'enabled'),
        Index('idx_governance_enabled_severity', 'enabled', 'severity'),
        Index('idx_governance_scope_action', 'scope', 'action'),
    )


class GovernanceRule(BaseModel):
    """
    Pydantic Governance Rule Model - API representation.
    """
    rule_id: UUID = Field(default_factory=uuid4, description="Unique rule identifier")
    name: str = Field(..., description="Rule name (unique)", min_length=1, max_length=255)
    description: str = Field(..., description="Rule description", min_length=1)
    condition: dict[str, Any] = Field(default_factory=dict, description="Rule condition logic")
    action: Action = Field(..., description="Action to take when rule is triggered")
    severity: Severity = Field(default=Severity.MEDIUM, description="Rule severity level")
    scope: str | None = Field(None, description="Rule scope (optional)")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @validator('name')
    def validate_name(cls, v):
        """Validate rule name."""
        if not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip()

    @validator('condition')
    def validate_condition(cls, v):
        """Validate rule condition."""
        if not isinstance(v, dict):
            raise ValueError("Condition must be a dictionary")
        return v


class GovernanceRuleCreate(BaseModel):
    """
    Governance Rule Creation Schema.
    """
    name: str = Field(..., description="Rule name", min_length=1, max_length=255)
    description: str = Field(..., description="Rule description", min_length=1)
    condition: dict[str, Any] = Field(default_factory=dict, description="Rule condition logic")
    action: Action = Field(..., description="Action to take")
    severity: Severity = Field(default=Severity.MEDIUM, description="Severity level")
    scope: str | None = Field(None, description="Rule scope")
    enabled: bool = Field(default=True, description="Enable rule")


class GovernanceRuleUpdate(BaseModel):
    """
    Governance Rule Update Schema.
    """
    description: str | None = Field(None, description="Rule description")
    condition: dict[str, Any] = Field(None, description="Rule condition logic")
    action: Action | None = Field(None, description="Action to take")
    severity: Severity | None = Field(None, description="Severity level")
    scope: str | None = Field(None, description="Rule scope")
    enabled: bool | None = Field(None, description="Enable/disable rule")


class GovernanceRuleResponse(BaseModel):
    """
    Governance Rule Response Schema.
    """
    rule_id: UUID
    name: str
    description: str
    condition: dict[str, Any]
    action: str
    severity: str
    scope: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class GatekeeperCheckRequest(BaseModel):
    """
    Request for gatekeeper validation check.
    """
    action_type: str = Field(..., description="Type of action to validate")
    actor: str = Field(..., description="Who is performing the action")
    scope: str = Field(..., description="Action scope/context")
    target_data: dict[str, Any] = Field(default_factory=dict, description="Target data for the action")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GatekeeperCheckResponse(BaseModel):
    """
    Response from gatekeeper validation check.
    """
    allowed: bool = Field(..., description="Whether action is allowed")
    action: str = Field(..., description="Recommended action (allow/warn/review/block/alternative)")
    reason: str = Field(..., description="Reason for the decision")
    triggered_rules: list[dict[str, Any]] = Field(default_factory=list, description="Rules that were triggered")
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Calculated risk score")
    alternatives: list[str] = Field(default_factory=list, description="Alternative approaches if blocked")
    warnings: list[str] = Field(default_factory=list, description="Warnings for the action")


class RiskAssessment(BaseModel):
    """
    Risk assessment result.
    """
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score (0-1)")
    risk_factors: list[dict[str, Any]] = Field(default_factory=list, description="Identified risk factors")
    severity: Severity = Field(..., description="Risk severity level")
    recommendations: list[str] = Field(default_factory=list, description="Risk mitigation recommendations")