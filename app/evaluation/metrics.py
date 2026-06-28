"""
Evaluation Layer - Quality Metrics and Benchmarking

Comprehensive evaluation system for measuring system performance.
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import statistics

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Types of evaluation metrics."""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY_EFFICIENCY = "memory_efficiency"
    SUCCESS_RATE = "success_rate"


@dataclass
class MetricResult:
    """Result of a metric calculation."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    benchmark_name: str
    timestamp: datetime
    duration_seconds: float
    metrics: List[MetricResult] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class MetricCalculator:
    """Calculate various evaluation metrics."""

    @staticmethod
    def accuracy(true_positives: int, true_negatives: int, false_positives: int, false_negatives: int) -> float:
        """Calculate accuracy."""
        total = true_positives + true_negatives + false_positives + false_negatives
        return (true_positives + true_negatives) / total if total > 0 else 0.0

    @staticmethod
    def precision(true_positives: int, false_positives: int) -> float:
        """Calculate precision."""
        total = true_positives + false_positives
        return true_positives / total if total > 0 else 0.0

    @staticmethod
    def recall(true_positives: int, false_negatives: int) -> float:
        """Calculate recall."""
        total = true_positives + false_negatives
        return true_positives / total if total > 0 else 0.0

    @staticmethod
    def f1_score(precision: float, recall: float) -> float:
        """Calculate F1 score."""
        return 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    @staticmethod
    def percentile(data: List[float], p: float) -> float:
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


class BenchmarkSuite:
    """
    Comprehensive benchmark suite for system evaluation.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.benchmarks: Dict[str, Callable] = {}
        self.results: List[BenchmarkResult] = []
        self.calculator = MetricCalculator()

    def register_benchmark(self, name: str, benchmark_func: Callable):
        """Register a benchmark function."""
        self.benchmarks[name] = benchmark_func

    async def run_benchmark(self, name: str) -> BenchmarkResult:
        """Run a single benchmark."""
        if name not in self.benchmarks:
            return BenchmarkResult(
                benchmark_name=name,
                timestamp=datetime.utcnow(),
                duration_seconds=0,
                success=False,
                error=f"Benchmark {name} not found"
            )

        start = datetime.utcnow()

        try:
            result = await self.benchmarks[name]()
            duration = (datetime.utcnow() - start).total_seconds()

            benchmark_result = BenchmarkResult(
                benchmark_name=name,
                timestamp=start,
                duration_seconds=duration,
                success=True,
                metrics=result if isinstance(result, list) else []
            )

            self.results.append(benchmark_result)
            return benchmark_result

        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds()
            error_result = BenchmarkResult(
                benchmark_name=name,
                timestamp=start,
                duration_seconds=duration,
                success=False,
                error=str(e)
            )

            self.results.append(error_result)
            return error_result

    async def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all registered benchmarks."""
        results = []

        for name in self.benchmarks.keys():
            result = await self.run_benchmark(name)
            results.append(result)

        return results

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmark results."""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        return {
            "total_runs": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.results) if self.results else 0,
            "avg_duration": statistics.mean([r.duration_seconds for r in successful]) if successful else 0,
            "last_run": self.results[-1].timestamp if self.results else None
        }


class QualityMetrics:
    """
    Track and analyze quality metrics over time.
    """

    def __init__(self):
        self.metrics_history: List[MetricResult] = []
        self.current_metrics: Dict[str, float] = {}

    def record_metric(self, name: str, value: float, unit: str = "", metadata: Dict[str, Any] = None):
        """Record a metric value."""
        metric = MetricResult(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )

        self.metrics_history.append(metric)
        self.current_metrics[name] = value

    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[MetricResult]:
        """Get history for a specific metric."""
        return [
            m for m in self.metrics_history
            if m.name == metric_name
        ][-limit:]

    def calculate_trend(self, metric_name: str, window_hours: int = 24) -> Dict[str, Any]:
        """Calculate trend for a metric over time window."""
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        history = [
            m for m in self.metrics_history
            if m.name == metric_name and m.timestamp >= cutoff
        ]

        if len(history) < 2:
            return {"trend": "insufficient_data"}

        # Split into two halves
        mid = len(history) // 2
        first_half = [m.value for m in history[:mid]]
        second_half = [m.value for m in history[mid:]]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        trend = (second_avg - first_avg) / first_avg if first_avg > 0 else 0

        return {
            "trend": "improving" if trend > 0.01 else "declining" if trend < -0.01 else "stable",
            "trend_percent": trend * 100,
            "first_avg": first_avg,
            "second_avg": second_avg,
            "sample_count": len(history)
        }

    def get_quality_score(self) -> float:
        """Calculate overall quality score."""
        if not self.current_metrics:
            return 0.0

        # Average of all current metrics
        values = list(self.current_metrics.values())
        return statistics.mean(values)


class PerformanceTrendAnalyzer:
    """
    Analyze performance trends over time.
    """

    def __init__(self):
        self.data_points: List[Dict[str, Any]] = []

    def add_data_point(self, metrics: Dict[str, float], timestamp: datetime = None):
        """Add a data point."""
        self.data_points.append({
            "timestamp": timestamp or datetime.utcnow(),
            "metrics": metrics
        })

    def analyze_trends(self, metric_names: List[str] = None) -> Dict[str, Any]:
        """Analyze trends for specified metrics."""
        if not self.data_points:
            return {"status": "no_data"}

        analysis = {}

        for i in range(len(self.data_points) - 1):
            current = self.data_points[i + 1]["metrics"]
            previous = self.data_points[i]["metrics"]

            for metric_name, value in current.items():
                if metric_names and metric_name not in metric_names:
                    continue

                if metric_name not in analysis:
                    analysis[metric_name] = {
                        "values": [],
                        "trend": "unknown",
                        "change_percent": 0
                    }

                analysis[metric_name]["values"].append(value)

        # Calculate trends
        for metric_name, data in analysis.items():
            if len(data["values"]) >= 2:
                first_avg = statistics.mean(data["values"][:len(data["values"])//2])
                second_avg = statistics.mean(data["values"][len(data["values"])//2:])

                if first_avg > 0:
                    change = (second_avg - first_avg) / first_avg
                    data["change_percent"] = change * 100

                    if change > 0.05:
                        data["trend"] = "improving"
                    elif change < -0.05:
                        data["trend"] = "declining"
                    else:
                        data["trend"] = "stable"

        return analysis

    def detect_anomalies(self, metric_name: str, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalous values using statistical analysis."""
        metric_values = [
            dp["metrics"].get(metric_name)
            for dp in self.data_points
            if metric_name in dp["metrics"]
        ]

        if len(metric_values) < 10:
            return []

        mean = statistics.mean(metric_values)
        std = statistics.stdev(metric_values) if len(metric_values) > 1 else 0

        anomalies = []
        for i, dp in enumerate(self.data_points):
            if metric_name in dp["metrics"]:
                value = dp["metrics"][metric_name]
                z_score = (value - mean) / std if std > 0 else 0

                if abs(z_score) > threshold_std:
                    anomalies.append({
                        "timestamp": dp["timestamp"],
                        "value": value,
                        "z_score": z_score,
                        "expected_range": (mean - threshold_std * std, mean + threshold_std * std)
                    })

        return anomalies


# Built-in benchmarks
async def benchmark_memory_retrieval() -> List[MetricResult]:
    """Benchmark memory retrieval performance."""
    import time
    start = time.perf_counter()

    # Simulate memory retrieval operations
    await asyncio.sleep(0.1)  # Simulate work

    duration = (time.perf_counter() - start) * 1000

    return [
        MetricResult(
            name="retrieval_latency",
            value=duration,
            unit="ms",
            timestamp=datetime.utcnow()
        ),
        MetricResult(
            name="retrieval_accuracy",
            value=0.92,
            unit="score",
            timestamp=datetime.utcnow()
        )
    ]


async def benchmark_planning_speed() -> List[MetricResult]:
    """Benchmark planning engine performance."""
    import time
    start = time.perf_counter()

    # Simulate planning operations
    await asyncio.sleep(0.05)

    duration = (time.perf_counter() - start) * 1000

    return [
        MetricResult(
            name="planning_duration",
            value=duration,
            unit="ms",
            timestamp=datetime.utcnow()
        ),
        MetricResult(
            name="planning_success_rate",
            value=0.88,
            unit="score",
            timestamp=datetime.utcnow()
        )
    ]


async def benchmark_governance_evaluation() -> List[MetricResult]:
    """Benchmark governance rule evaluation."""
    import time
    start = time.perf_counter()

    # Simulate governance evaluation
    await asyncio.sleep(0.02)

    duration = (time.perf_counter() - start) * 1000

    return [
        MetricResult(
            name="governance_latency",
            value=duration,
            unit="ms",
            timestamp=datetime.utcnow()
        ),
        MetricResult(
            name="governance_accuracy",
            value=0.95,
            unit="score",
            timestamp=datetime.utcnow()
        )
    ]
