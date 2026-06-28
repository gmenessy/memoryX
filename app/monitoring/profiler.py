"""
Performance Monitoring and Profiling Infrastructure

Provides comprehensive performance tracking for production systems.
"""
import time
import functools
import asyncio
from typing import Callable, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import psutil
import threading

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """A single performance measurement."""
    operation: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    operation: str
    count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    error_count: int = 0
    last_execution: Optional[datetime] = None

    @property
    def avg_duration_ms(self) -> float:
        """Average duration in milliseconds."""
        return self.total_duration_ms / self.count if self.count > 0 else 0.0

    @property
    def success_rate(self) -> float:
        """Success rate (0-1)."""
        if self.count == 0:
            return 1.0
        return (self.count - self.error_count) / self.count

    @property
    def p95_duration_ms(self) -> float:
        """Approximate 95th percentile (simplified)."""
        return self.max_duration_ms * 0.95 if self.count > 10 else self.max_duration_ms


class PerformanceProfiler:
    """
    Performance profiler for tracking operation performance.

    Usage:
        profiler = PerformanceProfiler()

        @profiler.profile_operation
        def my_function():
            # ... code ...
            pass

        # Or manually:
        with profiler.profile("database_query"):
            # ... code ...
            pass
    """

    def __init__(self, sample_rate: float = 1.0):
        """
        Initialize profiler.

        Args:
            sample_rate: Fraction of operations to sample (0.0-1.0)
        """
        self.sample_rate = sample_rate
        self.metrics: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self.recent_metrics: list[PerformanceMetric] = []
        self.max_recent_metrics = 1000
        self._lock = threading.Lock()

    def profile_operation(self, operation_name: str = None) -> Callable:
        """
        Decorator to profile an operation.

        Args:
            operation_name: Name for the operation (defaults to function name)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._track_sync(func, operation_name or func.__name__, *args, **kwargs)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._track_async(func, operation_name or func.__name__, *args, **kwargs)

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator

    def _track_sync(self, func: Callable, operation: str, *args, **kwargs):
        """Track synchronous function execution."""
        if self._should_sample():
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_metric(operation, duration_ms, True)
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_metric(operation, duration_ms, False, str(e))
                raise
        else:
            return func(*args, **kwargs)

    async def _track_async(self, func: Callable, operation: str, *args, **kwargs):
        """Track async function execution."""
        if self._should_sample():
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_metric(operation, duration_ms, True)
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                self._record_metric(operation, duration_ms, False, str(e))
                raise
        else:
            return await func(*args, **kwargs)

    def profile(self, operation: str, metadata: Dict[str, Any] = None):
        """
        Context manager for profiling a block of code.

        Args:
            operation: Name of the operation
            metadata: Optional metadata to attach
        """
        return ProfileContext(self, operation, metadata)

    def _should_sample(self) -> bool:
        """Determine if this operation should be sampled."""
        import random
        return random.random() < self.sample_rate

    def _record_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool,
        error: str = None
    ):
        """Record a performance metric."""
        with self._lock:
            stats = self.metrics[operation]
            stats.count += 1
            stats.total_duration_ms += duration_ms
            stats.min_duration_ms = min(stats.min_duration_ms, duration_ms)
            stats.max_duration_ms = max(stats.max_duration_ms, duration_ms)
            stats.last_execution = datetime.utcnow()

            if not success:
                stats.error_count += 1

            # Store recent metric
            metric = PerformanceMetric(
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                error=error
            )
            self.recent_metrics.append(metric)
            if len(self.recent_metrics) > self.max_recent_metrics:
                self.recent_metrics.pop(0)

    def get_stats(self, operation: str) -> Optional[PerformanceStats]:
        """Get statistics for a specific operation."""
        return self.metrics.get(operation)

    def get_all_stats(self) -> Dict[str, PerformanceStats]:
        """Get statistics for all operations."""
        return dict(self.metrics)

    def get_slow_operations(self, threshold_ms: float = 100.0, min_count: int = 5) -> list[tuple[str, PerformanceStats]]:
        """Get operations slower than threshold."""
        return [
            (op, stats)
            for op, stats in self.metrics.items()
            if stats.count >= min_count and stats.avg_duration_ms > threshold_ms
        ]

    def get_error_prone_operations(self, min_error_rate: float = 0.1, min_count: int = 5) -> list[tuple[str, PerformanceStats]]:
        """Get operations with high error rates."""
        return [
            (op, stats)
            for op, stats in self.metrics.items()
            if stats.count >= min_count and stats.success_rate < (1 - min_error_rate)
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        total_ops = sum(stats.count for stats in self.metrics.values())
        total_errors = sum(stats.error_count for stats in self.metrics.values())

        return {
            "total_operations": total_ops,
            "total_errors": total_errors,
            "overall_success_rate": (total_ops - total_errors) / total_ops if total_ops > 0 else 1.0,
            "unique_operations": len(self.metrics),
            "slow_operations": len(self.get_slow_operations()),
            "error_prone_operations": len(self.get_error_prone_operations()),
            "sample_rate": self.sample_rate
        }

    def reset(self):
        """Clear all metrics."""
        with self._lock:
            self.metrics.clear()
            self.recent_metrics.clear()


class ProfileContext:
    """Context manager for profiling code blocks."""

    def __init__(self, profiler: PerformanceProfiler, operation: str, metadata: Dict[str, Any] = None):
        self.profiler = profiler
        self.operation = operation
        self.metadata = metadata or {}
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start) * 1000
        success = exc_type is None
        error = str(exc_val) if exc_type else None

        self.profiler._record_metric(
            self.operation,
            duration_ms,
            success,
            error
        )


class SystemMonitor:
    """
    Monitor system resources (CPU, memory, etc.).
    """

    def __init__(self):
        self.process = psutil.Process()
        self.metrics_history: list[Dict[str, Any]] = []
        self.max_history = 100

    def capture_snapshot(self) -> Dict[str, Any]:
        """Capture current system state."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": self.process.cpu_percent(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "memory_percent": self.process.memory_percent(),
            "threads": self.process.num_threads(),
            "open_files": len(self.process.open_files()),
            "connections": len(self.process.connections()),
        }

        self.metrics_history.append(snapshot)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)

        return snapshot

    def get_current(self) -> Dict[str, Any]:
        """Get current system status."""
        return self.capture_snapshot()

    def get_average_stats(self, window_minutes: int = 5) -> Dict[str, Any]:
        """Get average stats over time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        window = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) >= cutoff
        ]

        if not window:
            return {}

        return {
            "avg_cpu": sum(m["cpu_percent"] for m in window) / len(window),
            "avg_memory_mb": sum(m["memory_mb"] for m in window) / len(window),
            "avg_threads": sum(m["threads"] for m in window) / len(window),
            "sample_count": len(window)
        }

    def check_thresholds(
        self,
        max_cpu: float = 80.0,
        max_memory_mb: float = 1000.0,
        max_memory_percent: float = 80.0
    ) -> Dict[str, Any]:
        """Check if system is within acceptable thresholds."""
        current = self.get_current()

        alerts = []
        if current["cpu_percent"] > max_cpu:
            alerts.append(f"High CPU usage: {current['cpu_percent']}%")
        if current["memory_mb"] > max_memory_mb:
            alerts.append(f"High memory usage: {current['memory_mb']:.1f} MB")
        if current["memory_percent"] > max_memory_percent:
            alerts.append(f"High memory percent: {current['memory_percent']}%")

        return {
            "healthy": len(alerts) == 0,
            "alerts": alerts,
            "current": current
        }


# Global profiler instance
default_profiler = PerformanceProfiler()
