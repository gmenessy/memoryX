"""
Performance Monitoring Infrastructure

Tracks system performance metrics for self-improvement.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID, uuid4
from enum import Enum
from collections import defaultdict
import statistics

from sqlalchemy import DateTime, Float, JSON, String, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MetricType(str, Enum):
    """Types of performance metrics."""
    MEMORY_RETRIEVAL = "memory_retrieval"
    PLANNING_SUCCESS = "planning_success"
    PLANNING_SPEED = "planning_speed"
    GOVERNANCE_ACCURACY = "governance_accuracy"
    GRAPH_QUERY_SPEED = "graph_query_speed"
    OVERALL_PERFORMANCE = "overall_performance"


class PerformanceMetricDB(Base):
    """
    SQLAlchemy Model for performance metrics.
    Stores time-series performance data.
    """
    __tablename__ = "performance_metrics"

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
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    metric_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",  # Column name remains 'metadata' in DB
        JSON,
        nullable=False,
        default={}
    )
    agent_id: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )


class PerformanceSnapshotDB(Base):
    """
    SQLAlchemy Model for performance snapshots.
    Stores aggregated performance for time periods.
    """
    __tablename__ = "performance_snapshots"

    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    metric_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    mean: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    median: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    min: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    max: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    percentile_90: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class EvolutionLogDB(Base):
    """
    SQLAlchemy Model for evolution history.
    Tracks all self-improvement actions.
    """
    __tablename__ = "evolution_logs"

    evolution_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    evolution_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    target_component: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    before_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    after_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    improvement_delta: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    validated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    rollback_safe: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )


class PerformanceMonitor:
    """
    Performance monitoring system for Darwin.

    Tracks metrics over time and provides analysis for self-improvement.
    """

    def __init__(self):
        self.metrics_buffer: List[Dict[str, Any]] = []
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.operation_success: Dict[str, int] = defaultdict(int)

    def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        metadata: Dict[str, Any] = None,
        agent_id: str = None,
        session_id: str = None
    ) -> None:
        """Record a performance metric."""
        metric = {
            "metric_type": metric_type.value,
            "value": value,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {},
            "agent_id": agent_id,
            "session_id": session_id
        }
        self.metrics_buffer.append(metric)

    def record_operation(self, operation_type: str, success: bool = True) -> None:
        """Record an operation occurrence."""
        self.operation_counts[operation_type] += 1
        if success:
            self.operation_success[operation_type] += 1

    def get_success_rate(self, operation_type: str) -> float:
        """Get success rate for an operation type."""
        total = self.operation_counts.get(operation_type, 0)
        if total == 0:
            return 0.0
        successes = self.operation_success.get(operation_type, 0)
        return successes / total

    def get_metric_statistics(
        self,
        metric_type: MetricType,
        time_window: timedelta = None
    ) -> Dict[str, float]:
        """Get statistics for a metric type."""
        now = datetime.utcnow()
        cutoff = now - time_window if time_window else datetime.min

        values = [
            m["value"] for m in self.metrics_buffer
            if m["metric_type"] == metric_type.value and m["timestamp"] >= cutoff
        ]

        if not values:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "percentile_90": 0.0
            }

        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "percentile_90": self._percentile(values, 90)
        }

    def _percentile(self, data: List[float], p: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = k - f
        if f + 1 < len(sorted_data):
            return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
        return sorted_data[f]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        summary = {}

        for metric_type in MetricType:
            stats = self.get_metric_statistics(metric_type)
            summary[metric_type.value] = stats

        # Add operation success rates
        summary["operation_success_rates"] = {
            op_type: self.get_success_rate(op_type)
            for op_type in self.operation_counts.keys()
        }

        return summary

    def identify_improvement_opportunities(self) -> List[Dict[str, Any]]:
        """Identify areas where improvement is needed."""
        opportunities = []

        # Check each metric type for potential improvements
        for metric_type in MetricType:
            stats = self.get_metric_statistics(metric_type)

            if stats["count"] < 10:  # Not enough data
                continue

            # Identify low-performing areas
            if stats["mean"] < 0.7:  # Below 70% threshold
                opportunities.append({
                    "metric_type": metric_type.value,
                    "current_value": stats["mean"],
                    "target_value": 0.9,
                    "improvement_potential": 0.9 - stats["mean"],
                    "priority": "HIGH" if stats["mean"] < 0.5 else "MEDIUM",
                    "sample_count": stats["count"]
                })

        return opportunities

    def clear_buffer(self) -> None:
        """Clear the metrics buffer."""
        self.metrics_buffer.clear()
        self.operation_counts.clear()
        self.operation_success.clear()


class ImprovementTracker:
    """
    Tracks improvements over time.
    """

    def __init__(self):
        self.baseline_metrics: Dict[str, float] = {}
        self.current_metrics: Dict[str, float] = {}
        self.evolution_history: List[Dict[str, Any]] = []

    def set_baseline(self, metrics: Dict[str, float]) -> None:
        """Set baseline metrics."""
        self.baseline_metrics = metrics.copy()

    def update_current(self, metrics: Dict[str, float]) -> None:
        """Update current metrics."""
        self.current_metrics = metrics.copy()

    def calculate_improvement(self, metric_type: str) -> float:
        """Calculate improvement from baseline."""
        baseline = self.baseline_metrics.get(metric_type, 0.0)
        current = self.current_metrics.get(metric_type, 0.0)

        if baseline == 0:
            return 0.0

        return ((current - baseline) / baseline) * 100

    def get_improvement_summary(self) -> Dict[str, Any]:
        """Get summary of all improvements."""
        summary = {
            "metrics": {},
            "overall_improvement": 0.0
        }

        total_improvement = 0.0
        count = 0

        for metric_type in self.baseline_metrics.keys():
            improvement = self.calculate_improvement(metric_type)
            summary["metrics"][metric_type] = {
                "baseline": self.baseline_metrics[metric_type],
                "current": self.current_metrics.get(metric_type, 0.0),
                "improvement_percent": improvement
            }
            total_improvement += improvement
            count += 1

        if count > 0:
            summary["overall_improvement"] = total_improvement / count

        summary["evolution_count"] = len(self.evolution_history)

        return summary

    def record_evolution(self, evolution: Dict[str, Any]) -> None:
        """Record an evolution event."""
        self.evolution_history.append({
            **evolution,
            "timestamp": datetime.utcnow().isoformat()
        })
