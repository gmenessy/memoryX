"""
Enhanced Health Check System

Comprehensive health monitoring for production systems.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import asyncio

from app.logging_config import get_logger
from app.monitoring.api_monitor import HealthChecker

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """
    Individual health check configuration.
    """

    def __init__(
        self,
        name: str,
        check_func: Callable,
        timeout: float = 5.0,
        critical: bool = False,
        description: str = ""
    ):
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
        self.critical = critical
        self.description = description

    async def execute(self) -> Dict[str, Any]:
        """Execute the health check."""
        start = datetime.utcnow()
        result = {
            "name": self.name,
            "status": HealthStatus.UNKNOWN,
            "duration_ms": 0.0,
            "message": "",
            "critical": self.critical,
            "description": self.description
        }

        try:
            # Execute with timeout
            check_result = await asyncio.wait_for(
                self._run_check(),
                timeout=self.timeout
            )

            # Process result
            if isinstance(check_result, dict):
                result.update(check_result)
                if "status" not in result:
                    result["status"] = HealthStatus.HEALTHY if check_result.get("healthy", True) else HealthStatus.UNHEALTHY
            elif isinstance(check_result, bool):
                result["status"] = HealthStatus.HEALTHY if check_result else HealthStatus.UNHEALTHY
                result["message"] = "Check passed" if check_result else "Check failed"
            else:
                result["status"] = HealthStatus.HEALTHY
                result["message"] = str(check_result)

        except asyncio.TimeoutError:
            result["status"] = HealthStatus.UNHEALTHY
            result["message"] = f"Check timed out after {self.timeout}s"

        except Exception as e:
            result["status"] = HealthStatus.UNHEALTHY
            result["message"] = f"Check error: {str(e)}"

        finally:
            duration = (datetime.utcnow() - start).total_seconds()
            result["duration_ms"] = duration * 1000

        return result

    async def _run_check(self):
        """Run the check function."""
        if asyncio.iscoroutinefunction(self.check_func):
            return await self.check_func()
        else:
            return await asyncio.to_thread(self.check_func)


class EnhancedHealthChecker:
    """
    Enhanced health checking system with dependency management.
    """

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.dependencies: Dict[str, List[str]] = {}  # check -> list of checks it depends on
        self.results: List[Dict[str, Any]] = []
        self.max_results = 100

    def add_check(
        self,
        name: str,
        check_func: Callable,
        timeout: float = 5.0,
        critical: bool = False,
        description: str = "",
        depends_on: List[str] = None
    ):
        """Add a health check."""
        check = HealthCheck(name, check_func, timeout, critical, description)
        self.checks[name] = check

        if depends_on:
            self.dependencies[name] = depends_on

    async def run_all(self, include_details: bool = True) -> Dict[str, Any]:
        """Run all health checks."""
        start_time = datetime.utcnow()

        # Determine execution order based on dependencies
        execution_order = self._resolve_dependencies()

        overall_status = HealthStatus.HEALTHY
        check_results = {}

        # Run checks in order
        for check_name in execution_order:
            if check_name not in self.checks:
                continue

            check = self.checks[check_name]
            result = await check.execute()
            check_results[check_name] = result

            # Update overall status
            if result["status"] == HealthStatus.UNHEALTHY:
                if check.critical:
                    overall_status = HealthStatus.UNHEALTHY
                elif overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
            elif result["status"] == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        duration = (datetime.utcnow() - start_time).total_seconds()

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration * 1000,
            "overall_status": overall_status,
            "checks": check_results if include_details else {k: v["status"] for k, v in check_results.items()},
            "summary": self._get_summary(check_results)
        }

        # Store results
        self.results.append(summary)
        if len(self.results) > self.max_results:
            self.results.pop(0)

        return summary

    def _resolve_dependencies(self) -> List[str]:
        """Resolve check execution order based on dependencies."""
        executed = set()
        order = []

        def add_check(check_name: str):
            if check_name in executed or check_name not in self.checks:
                return

            # Add dependencies first
            for dep in self.dependencies.get(check_name, []):
                add_check(dep)

            order.append(check_name)
            executed.add(check_name)

        for check_name in self.checks.keys():
            add_check(check_name)

        return order

    def _get_summary(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of health check results."""
        total = len(results)
        healthy = sum(1 for r in results.values() if r.get("status") == HealthStatus.HEALTHY)
        degraded = sum(1 for r in results.values() if r.get("status") == HealthStatus.DEGRADED)
        unhealthy = sum(1 for r in results.values() if r.get("status") == HealthStatus.UNHEALTHY)
        critical_unhealthy = sum(
            1 for r in results.values()
            if r.get("status") == HealthStatus.UNHEALTHY and r.get("critical", False)
        )

        return {
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "critical_unhealthy": critical_unhealthy
        }

    async def quick_check(self) -> Dict[str, Any]:
        """Quick health check for load balancers."""
        critical_checks = [
            (name, check) for name, check in self.checks.items()
            if check.critical
        ]

        # Run critical checks only
        for name, check in critical_checks:
            result = await check.execute()
            if result["status"] != HealthStatus.HEALTHY:
                return {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "failing_check": name,
                    "message": result.get("message", "Check failed")
                }

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "All critical checks passed"
        }

    def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check results."""
        return self.results[-limit:]


# Built-in health check functions
async def check_api_reachability() -> Dict[str, Any]:
    """Check if API is reachable."""
    return {"status": HealthStatus.HEALTHY, "message": "API is responding"}


async def check_database_connection(session_factory) -> Callable:
    """Factory function that returns a database check."""
    async def _check() -> Dict[str, Any]:
        try:
            async with session_factory() as session:
                await session.execute("SELECT 1")
            return {"status": HealthStatus.HEALTHY, "message": "Database responding"}
        except Exception as e:
            return {"status": HealthStatus.UNHEALTHY, "message": f"Database error: {str(e)}"}
    return _check


async def check_cache_connection(cache_client) -> Callable:
    """Factory function that returns a cache check."""
    async def _check() -> Dict[str, Any]:
        try:
            await cache_client.ping()
            return {"status": HealthStatus.HEALTHY, "message": "Cache responding"}
        except Exception as e:
            return {"status": HealthStatus.DEGRADED, "message": f"Cache error: {str(e)}"}
    return _check


def check_memory_usage(threshold_mb: float = 1000.0) -> Dict[str, Any]:
    """Check memory usage."""
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024

    if memory_mb > threshold_mb:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"High memory usage: {memory_mb:.1f} MB",
            "memory_mb": memory_mb,
            "threshold_mb": threshold_mb
        }

    return {
        "status": HealthStatus.HEALTHY,
        "message": f"Memory usage OK: {memory_mb:.1f} MB",
        "memory_mb": memory_mb,
        "threshold_mb": threshold_mb
    }


def check_disk_space(path: str = "/", min_free_gb: float = 1.0) -> Dict[str, Any]:
    """Check disk space."""
    import psutil
    disk = psutil.disk_usage(path)
    free_gb = disk.free / (1024**3)

    if free_gb < min_free_gb:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Low disk space: {free_gb:.2f} GB free",
            "path": path,
            "free_gb": free_gb,
            "min_free_gb": min_free_gb
        }

    return {
        "status": HealthStatus.HEALTHY,
        "message": f"Disk space OK: {free_gb:.2f} GB free",
        "path": path,
        "free_gb": free_gb
    }


def check_cpu_usage(threshold_percent: float = 80.0) -> Dict[str, Any]:
    """Check CPU usage."""
    import psutil
    cpu_percent = psutil.cpu_percent(interval=1)

    if cpu_percent > threshold_percent:
        return {
            "status": HealthStatus.DEGRADED,
            "message": f"High CPU usage: {cpu_percent:.1f}%",
            "cpu_percent": cpu_percent,
            "threshold_percent": threshold_percent
        }

    return {
        "status": HealthStatus.HEALTHY,
        "message": f"CPU usage OK: {cpu_percent:.1f}%",
        "cpu_percent": cpu_percent
    }
