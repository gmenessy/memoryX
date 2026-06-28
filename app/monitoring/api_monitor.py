"""
API Monitoring and Health Check Infrastructure

Comprehensive monitoring for FastAPI applications.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import asyncio

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging_config import get_logger
from app.monitoring.profiler import PerformanceProfiler

logger = get_logger(__name__)


class APIMetrics:
    """Track API endpoint performance."""

    def __init__(self):
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_duration_ms": 0.0,
            "min_duration_ms": float('inf'),
            "max_duration_ms": 0.0,
            "error_count": 0,
            "status_codes": defaultdict(int),
            "last_called": None
        })

    def record_call(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        error: bool = False
    ):
        """Record an API call."""
        key = f"{method} {path}"
        stats = self.endpoint_stats[key]

        stats["count"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["min_duration_ms"] = min(stats["min_duration_ms"], duration_ms)
        stats["max_duration_ms"] = max(stats["max_duration_ms"], duration_ms)
        stats["status_codes"][status_code] += 1
        stats["last_called"] = datetime.utcnow()

        if error or status_code >= 500:
            stats["error_count"] += 1

    def get_stats(self, method: str = None, path: str = None) -> Dict[str, Any]:
        """Get statistics for endpoints."""
        results = {}

        for key, stats in self.endpoint_stats.items():
            if method and not key.startswith(method):
                continue
            if path and path not in key:
                continue

            results[key] = {
                "count": stats["count"],
                "avg_duration_ms": stats["total_duration_ms"] / stats["count"] if stats["count"] > 0 else 0,
                "min_duration_ms": stats["min_duration_ms"] if stats["min_duration_ms"] != float('inf') else 0,
                "max_duration_ms": stats["max_duration_ms"],
                "error_rate": stats["error_count"] / stats["count"] if stats["count"] > 0 else 0,
                "status_codes": dict(stats["status_codes"]),
                "last_called": stats["last_called"]
            }

        return results

    def get_slow_endpoints(self, threshold_ms: float = 500.0) -> List[Dict[str, Any]]:
        """Get endpoints slower than threshold."""
        results = []

        for key, stats in self.endpoint_stats.items():
            if stats["count"] > 0:
                avg_ms = stats["total_duration_ms"] / stats["count"]
                if avg_ms > threshold_ms:
                    results.append({
                        "endpoint": key,
                        "avg_duration_ms": avg_ms,
                        "count": stats["count"],
                        "max_duration_ms": stats["max_duration_ms"]
                    })

        return sorted(results, key=lambda x: x["avg_duration_ms"], reverse=True)

    def get_error_prone_endpoints(self, min_error_rate: float = 0.05) -> List[Dict[str, Any]]:
        """Get endpoints with high error rates."""
        results = []

        for key, stats in self.endpoint_stats.items():
            if stats["count"] >= 10:
                error_rate = stats["error_count"] / stats["count"]
                if error_rate > min_error_rate:
                    results.append({
                        "endpoint": key,
                        "error_rate": error_rate,
                        "error_count": stats["error_count"],
                        "total_calls": stats["count"]
                    })

        return sorted(results, key=lambda x: x["error_rate"], reverse=True)


class APIMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor API performance."""

    def __init__(
        self,
        app: ASGIApp,
        metrics: APIMetrics = None,
        profiler: PerformanceProfiler = None
    ):
        super().__init__(app)
        self.metrics = metrics or APIMetrics()
        self.profiler = profiler or PerformanceProfiler(sample_rate=0.1)

    async def dispatch(self, request: Request, call_next):
        """Process request and record metrics."""
        start_time = asyncio.get_event_loop().time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        # Record metrics
        self.metrics.record_call(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            error=response.status_code >= 500
        )

        return response


class HealthChecker:
    """
    Comprehensive health checking system.
    """

    def __init__(self):
        self.checks: Dict[str, Any] = {}
        self.last_check_results: Dict[str, Dict[str, Any]] = {}
        self.check_history: List[Dict[str, Any]] = []

    def register_check(self, name: str, check_func: callable, critical: bool = False):
        """Register a health check."""
        self.checks[name] = {
            "func": check_func,
            "critical": critical
        }

    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }

        critical_failed = False

        for name, check_config in self.checks.items():
            check_start = asyncio.get_event_loop().time()
            check_result = {
                "status": "unknown",
                "duration_ms": 0,
                "message": "",
                "critical": check_config["critical"]
            }

            try:
                result = await check_config["func"]() if asyncio.iscoroutinefunction(check_config["func"]) else check_config["func"]()

                if isinstance(result, dict):
                    check_result.update(result)
                elif isinstance(result, bool):
                    check_result["status"] = "healthy" if result else "unhealthy"
                    check_result["message"] = "Check passed" if result else "Check failed"
                else:
                    check_result["message"] = str(result)

                # Determine status
                if check_result.get("status") == "unhealthy":
                    results["checks"][name] = check_result
                    if check_config["critical"]:
                        critical_failed = True
                        results["overall_status"] = "unhealthy"
                else:
                    results["checks"][name] = check_result

            except Exception as e:
                check_result["status"] = "error"
                check_result["message"] = f"Check error: {str(e)}"
                results["checks"][name] = check_result
                if check_config["critical"]:
                    critical_failed = True
                    results["overall_status"] = "unhealthy"

            finally:
                check_result["duration_ms"] = (asyncio.get_event_loop().time() - check_start) * 1000

        # Store results
        self.last_check_results = results
        self.check_history.append(results)
        if len(self.check_history) > 100:
            self.check_history.pop(0)

        return results

    async def quick_health(self) -> Dict[str, Any]:
        """Quick health check for load balancers."""
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "checks_run": len(self.checks)
        }

    def get_uptime(self) -> Dict[str, Any]:
        """Get uptime statistics."""
        if not self.check_history:
            return {"uptime_seconds": 0, "checks_performed": 0}

        start_time = datetime.fromisoformat(self.check_history[0]["timestamp"])
        uptime = (datetime.utcnow() - start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "uptime_hours": uptime / 3600,
            "checks_performed": len(self.check_history),
            "avg_check_frequency": len(self.check_history) / (uptime / 60) if uptime > 0 else 0
        }


# Built-in health checks
async def check_database(session_factory) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        async with session_factory() as session:
            await session.execute("SELECT 1")
        return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Database error: {str(e)}"}


async def check_memory(max_mb: float = 1000.0) -> Dict[str, Any]:
    """Check memory usage."""
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024

    if memory_mb > max_mb:
        return {
            "status": "unhealthy",
            "message": f"High memory usage: {memory_mb:.1f} MB",
            "memory_mb": memory_mb
        }

    return {
        "status": "healthy",
        "message": f"Memory usage OK: {memory_mb:.1f} MB",
        "memory_mb": memory_mb
    }


def check_disk(min_free_gb: float = 1.0) -> Dict[str, Any]:
    """Check disk space."""
    import psutil
    disk = psutil.disk_usage('/')
    free_gb = disk.free / (1024**3)

    if free_gb < min_free_gb:
        return {
            "status": "unhealthy",
            "message": f"Low disk space: {free_gb:.2f} GB free",
            "free_gb": free_gb
        }

    return {
        "status": "healthy",
        "message": f"Disk space OK: {free_gb:.2f} GB free",
        "free_gb": free_gb
    }
