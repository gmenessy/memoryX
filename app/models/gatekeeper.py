"""
Gatekeeper Model - Memory Action Validation

The Gatekeeper is the most critical component.
Before ANY action, it checks: Is this action sensible?

Checks:
- Policies
- Risks
- Past failures
- Conflicts
- Scope

Actions:
- allow
- warn
- review
- block
- alternative
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GatekeeperAction(str, Enum):
    """
    Possible Gatekeeper actions.
    """
    ALLOW = "allow"              # Action is approved
    WARN = "warn"                # Action needs warning
    REVIEW = "review"            # Action needs manual review
    BLOCK = "block"              # Action is blocked
    ALTERNATIVE = "alternative"  # Alternative action suggested


class PolicySeverity(str, Enum):
    """
    Policy severity levels.
    """
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    """
    Risk assessment levels.
    """
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"


class PolicyDB(Base):
    """
    SQLAlchemy Policy Model - Database representation.
    Stores governance policies that the Gatekeeper enforces.
    """
    __tablename__ = "policies"

    policy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
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
        default="medium"
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    active: Mapped[bool] = mapped_column(
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


class RiskAssessmentDB(Base):
    """
    SQLAlchemy Risk Assessment Model - Database representation.
    Stores risk assessments for actions.
    """
    __tablename__ = "risk_assessments"

    assessment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    risk_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    risk_factors: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    mitigation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class GatekeeperCheckDB(Base):
    """
    SQLAlchemy Gatekeeper Check Model - Database representation.
    Stores history of all gatekeeper checks for audit trail.
    """
    __tablename__ = "gatekeeper_checks"

    check_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    result: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    policies_matched: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=[]
    )
    risks_found: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=[]
    )
    conflicts: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    alternative_suggested: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    actor: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# Pydantic Models for API


class Policy(BaseModel):
    """
    Pydantic Policy Model - API representation.
    """
    policy_id: UUID = Field(default_factory=uuid4, description="Unique policy identifier")
    name: str = Field(..., description="Policy name (unique)", min_length=1, max_length=255)
    description: str = Field(..., description="Policy description", min_length=1)
    condition: dict[str, Any] = Field(default_factory=dict, description="Policy condition (JSON)")
    action: str = Field(..., description="Action to take when condition matches")
    severity: str = Field(default="medium", description="Policy severity")
    scope: str = Field(..., description="Policy scope", min_length=1)
    active: bool = Field(default=True, description="Whether policy is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @field_validator('action')
    def validate_action(cls, v):
        """Validate action is one of the allowed actions."""
        allowed_actions = [a.value for a in GatekeeperAction]
        if v not in allowed_actions:
            raise ValueError(f"Invalid action: {v}. Must be one of: {', '.join(allowed_actions)}")
        return v

    @field_validator('severity')
    def validate_severity(cls, v):
        """Validate severity is one of the allowed severities."""
        allowed_severities = [s.value for s in PolicySeverity]
        if v not in allowed_severities:
            raise ValueError(f"Invalid severity: {v}. Must be one of: {', '.join(allowed_severities)}")
        return v


class PolicyCreate(BaseModel):
    """
    Policy Creation Schema.
    """
    name: str = Field(..., description="Policy name", min_length=1, max_length=255)
    description: str = Field(..., description="Policy description", min_length=1)
    condition: dict[str, Any] = Field(default_factory=dict, description="Policy condition")
    action: str = Field(..., description="Action to take")
    severity: str = Field(default="medium", description="Policy severity")
    scope: str = Field(..., description="Policy scope", min_length=1)
    active: bool = Field(default=True, description="Whether policy is active")


class PolicyUpdate(BaseModel):
    """
    Policy Update Schema.
    """
    description: str | None = Field(None, description="Policy description", min_length=1)
    condition: dict[str, Any] = Field(None, description="Policy condition")
    action: str | None = Field(None, description="Action to take")
    severity: str | None = Field(None, description="Policy severity")
    active: bool | None = Field(None, description="Whether policy is active")


class PolicyResponse(BaseModel):
    """
    Policy Response Schema.
    """
    policy_id: UUID
    name: str
    description: str
    condition: dict[str, Any]
    action: str
    severity: str
    scope: str
    active: bool
    created_at: datetime
    updated_at: datetime


class RiskAssessment(BaseModel):
    """
    Pydantic Risk Assessment Model - API representation.
    """
    assessment_id: UUID = Field(default_factory=uuid4, description="Unique assessment identifier")
    action_type: str = Field(..., description="Type of action being assessed", min_length=1)
    risk_level: str = Field(..., description="Risk level")
    risk_factors: dict[str, Any] = Field(default_factory=dict, description="Risk factors (JSON)")
    mitigation: str | None = Field(None, description="Mitigation strategy")
    scope: str = Field(..., description="Assessment scope", min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @field_validator('risk_level')
    def validate_risk_level(cls, v):
        """Validate risk level is one of the allowed levels."""
        allowed_levels = [r.value for r in RiskLevel]
        if v not in allowed_levels:
            raise ValueError(f"Invalid risk_level: {v}. Must be one of: {', '.join(allowed_levels)}")
        return v


class RiskAssessmentCreate(BaseModel):
    """
    Risk Assessment Creation Schema.
    """
    action_type: str = Field(..., description="Type of action", min_length=1)
    risk_level: str = Field(..., description="Risk level")
    risk_factors: dict[str, Any] = Field(default_factory=dict, description="Risk factors")
    mitigation: str | None = Field(None, description="Mitigation strategy")
    scope: str = Field(..., description="Assessment scope", min_length=1)


class RiskAssessmentResponse(BaseModel):
    """
    Risk Assessment Response Schema.
    """
    assessment_id: UUID
    action_type: str
    risk_level: str
    risk_factors: dict[str, Any]
    mitigation: str | None
    scope: str
    created_at: datetime


class GatekeeperCheck(BaseModel):
    """
    Pydantic Gatekeeper Check Model - API representation.
    """
    check_id: UUID = Field(default_factory=uuid4, description="Unique check identifier")
    action: str = Field(..., description="Action being checked", min_length=1)
    result: str = Field(..., description="Check result")
    reason: str = Field(..., description="Reason for result", min_length=1)
    policies_matched: list[UUID] = Field(default_factory=list, description="Matched policy IDs")
    risks_found: list[UUID] = Field(default_factory=list, description="Found risk IDs")
    conflicts: dict[str, Any] = Field(default_factory=dict, description="Conflicts detected")
    alternative_suggested: str | None = Field(None, description="Suggested alternative action")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in result")
    scope: str = Field(..., description="Check scope", min_length=1)
    actor: str = Field(..., description="Who initiated the action", min_length=1)
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")

    @field_validator('result')
    def validate_result(cls, v):
        """Validate result is one of the allowed results."""
        allowed_results = [a.value for a in GatekeeperAction]
        if v not in allowed_results:
            raise ValueError(f"Invalid result: {v}. Must be one of: {', '.join(allowed_results)}")
        return v


class GatekeeperCheckCreate(BaseModel):
    """
    Gatekeeper Check Creation Schema - Input for checking actions.
    """
    action: str = Field(..., description="Action to check", min_length=1)
    scope: str = Field(..., description="Action scope", min_length=1)
    actor: str = Field(..., description="Who is initiating", min_length=1)
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class GatekeeperCheckResponse(BaseModel):
    """
    Gatekeeper Check Response Schema.
    """
    check_id: UUID
    action: str
    result: str
    reason: str
    policies_matched: list[UUID]
    risks_found: list[UUID]
    conflicts: dict[str, Any]
    alternative_suggested: str | None
    confidence: float
    scope: str
    actor: str
    checked_at: datetime


class GatekeeperDecision(BaseModel):
    """
    Gatekeeper Decision Output - The result of a check.
    """
    allowed: bool = Field(..., description="Whether action is allowed")
    action: GatekeeperAction = Field(..., description="Recommended gatekeeper action")
    reason: str = Field(..., description="Human-readable reason", min_length=1)
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    blocked_policies: list[UUID] = Field(default_factory=list, description="Policies that blocked")
    risks: list[UUID] = Field(default_factory=list, description="Risk assessments")
    alternative: str | None = Field(None, description="Suggested alternative")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score")
    check_id: UUID = Field(..., description="Reference check ID")


# Constants

POLICY_ACTIONS = [a.value for a in GatekeeperAction]
SEVERITY_LEVELS = [s.value for s in PolicySeverity]
RISK_LEVELS = [r.value for r in RiskLevel]

# Example policies from specification
EXAMPLE_POLICIES = [
    {
        "name": "no_deploy_without_snapshot",
        "description": "Kein Deploy ohne Snapshot",
        "condition": {"action": "deploy", "has_snapshot": False},
        "action": "block",
        "severity": "high"
    },
    {
        "name": "avoid_known_failures",
        "description": "Bekannten Fehler nicht erneut ausführen",
        "condition": {"known_failure": True},
        "action": "warn",
        "severity": "medium"
    },
    {
        "name": "memory_conflict_check",
        "description": "Prüft auf Memory-Konflikte",
        "condition": {"has_conflict": True},
        "action": "review",
        "severity": "medium"
    }
]
