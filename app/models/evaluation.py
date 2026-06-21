"""
Evaluation Models - Quality Metrics and Performance Tracking
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator
from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MetricType(str, Enum):
    """Types of evaluation metrics."""
    MEMORY_PRECISION = "memory_precision"
    MEMORY_RECALL = "memory_recall"
    CASE_LEAKAGE = "case_leakage"
    POLICY_COMPLIANCE = "policy_compliance"
    RETRIEVAL_DRIFT = "retrieval_drift"
    GATEKEEPER_ACCURACY = "gatekeeper_accuracy"
    REPEATED_FAILURE_AVOIDANCE = "repeated_failure_avoidance"


class MetricLevel(str, Enum):
    """Severity levels for metrics."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    WARNING = "warning"
    CRITICAL = "critical"


class EvaluationMetricDB(Base):
    """
    SQLAlchemy Evaluation Metric Model - Database representation.
    Stores quality metrics and performance indicators.
    """
    __tablename__ = "evaluation_metrics"

    metric_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    metric_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    metric_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    metric_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class BenchmarkResultDB(Base):
    """
    SQLAlchemy Benchmark Result Model - Database representation.
    Stores results of benchmark runs.
    """
    __tablename__ = "benchmark_results"

    benchmark_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    benchmark_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    suite_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    results: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False
    )
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    duration_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class EvaluationMetric(BaseModel):
    """
    Pydantic Evaluation Metric Model - API representation.
    """
    metric_id: UUID = Field(default_factory=uuid4, description="Unique metric identifier")
    metric_type: MetricType = Field(..., description="Type of metric")
    metric_value: float = Field(..., ge=0.0, le=1.0, description="Metric value (0-1)")
    metric_level: MetricLevel = Field(..., description="Performance level")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    scope: str | None = Field(None, description="Metric scope")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metric timestamp")

    @validator('metric_value')
    def validate_metric_value(cls, v):
        """Validate metric value is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Metric value must be between 0.0 and 1.0")
        return v


class BenchmarkResult(BaseModel):
    """
    Pydantic Benchmark Result Model - API representation.
    """
    benchmark_id: UUID = Field(default_factory=uuid4, description="Unique benchmark identifier")
    benchmark_name: str = Field(..., description="Benchmark name")
    suite_name: str = Field(..., description="Suite name")
    results: dict[str, Any] = Field(default_factory=dict, description="Benchmark results")
    passed: bool = Field(..., description="Whether benchmark passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Benchmark score (0-1)")
    duration_ms: float = Field(..., description="Execution time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Benchmark timestamp")


class EvaluationReport(BaseModel):
    """
    Comprehensive evaluation report.
    """
    report_id: UUID = Field(default_factory=uuid4, description="Unique report identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report timestamp")
    scope: str | None = Field(None, description="Report scope")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall system score (0-1)")
    metrics: dict[str, EvaluationMetric] = Field(default_factory=dict, description="Individual metrics")
    recommendations: list[str] = Field(default_factory=list, description="Improvement recommendations")
    critical_issues: list[str] = Field(default_factory=list, description="Critical issues found")
    performance_trend: str = Field(..., description="Performance trend (improving/stable/degrading)")


class BenchmarkSuite(BaseModel):
    """
    Benchmark suite definition.
    """
    suite_name: str = Field(..., description="Suite name")
    benchmarks: list[str] = Field(default_factory=list, description="Benchmark names")
    description: str = Field(..., description="Suite description")
    min_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum passing score")


class BenchmarkExecutionRequest(BaseModel):
    """
    Request to execute benchmarks.
    """
    suite_name: str = Field(..., description="Suite to execute")
    benchmark_names: list[str] = Field(default_factory=list, description="Specific benchmarks (empty = all)")
    context: dict[str, Any] = Field(default_factory=dict, description="Execution context")


class BenchmarkExecutionResult(BaseModel):
    """
    Result of benchmark execution.
    """
    suite_name: str = Field(..., description="Suite name")
    total_benchmarks: int = Field(..., description="Total benchmarks executed")
    passed: int = Field(..., description="Number of passed benchmarks")
    failed: int = Field(..., description="Number of failed benchmarks")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall score")
    duration_ms: float = Field(..., description="Total execution time")
    results: list[BenchmarkResult] = Field(default_factory=list, description="Individual benchmark results")


# Metric types and thresholds for easy reference
METRIC_TYPES = [metric_type.value for metric_type in MetricType]
METRIC_THRESHOLDS = {
    "excellent": 0.9,
    "good": 0.75,
    "acceptable": 0.6,
    "warning": 0.45,
    "critical": 0.0
}


def calculate_metric_level(value: float) -> str:
    """
    Calculate metric level from value.

    Args:
        value: Metric value (0-1)

    Returns:
        Metric level (excellent/good/acceptable/warning/critical)
    """
    if value >= METRIC_THRESHOLDS["excellent"]:
        return "excellent"
    elif value >= METRIC_THRESHOLDS["good"]:
        return "good"
    elif value >= METRIC_THRESHOLDS["acceptable"]:
        return "acceptable"
    elif value >= METRIC_THRESHOLDS["warning"]:
        return "warning"
    else:
        return "critical"