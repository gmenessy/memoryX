"""
Evaluation Service - Business Logic Layer for Quality Metrics
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import (
    EvaluationMetric,
    EvaluationReport,
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkExecutionRequest,
    BenchmarkExecutionResult,
    METRIC_TYPES,
    calculate_metric_level
)
from app.repositories.evaluation_repository import EvaluationRepository


class EvaluationService:
    """
    Service layer for Evaluation Layer operations.
    Handles quality metrics and benchmark execution.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.evaluation_repo = EvaluationRepository(session)

    async def run_full_evaluation(self, scope: str | None = None) -> EvaluationReport:
        """
        Run comprehensive evaluation of the system.

        Args:
            scope: Optional scope for evaluation

        Returns:
            Comprehensive evaluation report
        """
        from app.models.evaluation import EvaluationMetric, MetricType, MetricLevel

        # Calculate all metrics
        metrics = {}

        # Memory precision
        precision_value = await self.evaluation_repo.calculate_memory_precision(scope)
        metrics["memory_precision"] = EvaluationMetric(
            metric_type=MetricType.MEMORY_PRECISION,
            metric_value=precision_value,
            metric_level=MetricLevel(calculate_metric_level(precision_value)),
            context={"scope": scope}
        )

        # Memory recall
        recall_value = await self.evaluation_repo.calculate_memory_recall(scope)
        metrics["memory_recall"] = EvaluationMetric(
            metric_type=MetricType.MEMORY_RECALL,
            metric_value=recall_value,
            metric_level=MetricLevel(calculate_metric_level(recall_value)),
            context={"scope": scope}
        )

        # Case leakage
        leakage_value = await self.evaluation_repo.calculate_case_leakage(scope)
        metrics["case_leakage"] = EvaluationMetric(
            metric_type=MetricType.CASE_LEAKAGE,
            metric_value=leakage_value,
            metric_level=MetricLevel(calculate_metric_level(leakage_value)),
            context={"scope": scope}
        )

        # Policy compliance
        compliance_value = await self.evaluation_repo.calculate_policy_compliance(scope)
        metrics["policy_compliance"] = EvaluationMetric(
            metric_type=MetricType.POLICY_COMPLIANCE,
            metric_value=compliance_value,
            metric_level=MetricLevel(calculate_metric_level(compliance_value)),
            context={"scope": scope}
        )

        # Retrieval drift
        drift_value = await self.evaluation_repo.calculate_retrieval_drift(scope)
        metrics["retrieval_drift"] = EvaluationMetric(
            metric_type=MetricType.RETRIEVAL_DRIFT,
            metric_value=drift_value,
            metric_level=MetricLevel(calculate_metric_level(1.0 - drift_value)),  # Invert for level
            context={"scope": scope}
        )

        # Gatekeeper accuracy
        gatekeeper_value = await self.evaluation_repo.calculate_gatekeeper_accuracy(scope)
        metrics["gatekeeper_accuracy"] = EvaluationMetric(
            metric_type=MetricType.GATEKEEPER_ACCURACY,
            metric_value=gatekeeper_value,
            metric_level=MetricLevel(calculate_metric_level(gatekeeper_value)),
            context={"scope": scope}
        )

        # Repeated failure avoidance
        failure_value = await self.evaluation_repo.calculate_repeated_failure_avoidance(scope)
        metrics["repeated_failure_avoidance"] = EvaluationMetric(
            metric_type=MetricType.REPEATED_FAILURE_AVOIDANCE,
            metric_value=failure_value,
            metric_level=MetricLevel(calculate_metric_level(failure_value)),
            context={"scope": scope}
        )

        # Save metrics to database
        for metric in metrics.values():
            await self.evaluation_repo.create_metric(metric)

        # Calculate overall score
        overall_score = sum(m.metric_value for m in metrics.values()) / len(metrics)

        # Generate recommendations and identify critical issues
        recommendations = []
        critical_issues = []

        for metric_name, metric in metrics.items():
            if metric.metric_level.value == "critical":
                critical_issues.append(f"{metric_name}: {metric.metric_value:.2f} - Critical level")
                recommendations.append(f"Address {metric_name} immediately")
            elif metric.metric_level.value == "warning":
                recommendations.append(f"Monitor and improve {metric_name}")

        # Determine performance trend
        performance_trend = await self._calculate_performance_trend(scope)

        return EvaluationReport(
            scope=scope,
            overall_score=overall_score,
            metrics=metrics,
            recommendations=recommendations,
            critical_issues=critical_issues,
            performance_trend=performance_trend
        )

    async def _calculate_performance_trend(self, scope: str | None = None) -> str:
        """
        Calculate performance trend over time.

        Args:
            scope: Filter by scope

        Returns:
            Performance trend (improving/stable/degrading)
        """
        # Get metrics from different time periods
        recent_metrics = await self.evaluation_repo.get_metrics(
            scope=scope,
            time_window_hours=24
        )

        if len(recent_metrics) < 2:
            return "stable"

        # Calculate trend
        recent_avg = sum(m.metric_value for m in recent_metrics) / len(recent_metrics)
        older_metrics = await self.evaluation_repo.get_metrics(
            scope=scope,
            time_window_hours=168  # 7 days
        )

        if older_metrics:
            older_avg = sum(m.metric_value for m in older_metrics) / len(older_metrics)

            if recent_avg > older_avg + 0.05:
                return "improving"
            elif recent_avg < older_avg - 0.05:
                return "degrading"
            else:
                return "stable"

        return "stable"

    async def execute_benchmark_suite(
        self,
        suite_name: str,
        benchmark_names: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> BenchmarkExecutionResult:
        """
        Execute a benchmark suite.

        Args:
            suite_name: Name of benchmark suite
            benchmark_names: Specific benchmarks to run (None = all)
            context: Execution context

        Returns:
            Benchmark execution result
        """
        # Define benchmark suites
        suites = {
            "core_metrics": {
                "description": "Core system metrics",
                "benchmarks": [
                    "memory_precision_test",
                    "memory_recall_test",
                    "policy_compliance_test"
                ],
                "min_score": 0.7
            },
            "advanced_metrics": {
                "description": "Advanced system metrics",
                "benchmarks": [
                    "case_leakage_test",
                    "retrieval_drift_test",
                    "gatekeeper_accuracy_test"
                ],
                "min_score": 0.65
            },
            "full_evaluation": {
                "description": "Complete system evaluation",
                "benchmarks": [
                    "memory_precision_test",
                    "memory_recall_test",
                    "case_leakage_test",
                    "policy_compliance_test",
                    "retrieval_drift_test",
                    "gatekeeper_accuracy_test",
                    "repeated_failure_avoidance_test"
                ],
                "min_score": 0.7
            }
        }

        if suite_name not in suites:
            raise ValueError(f"Unknown suite: {suite_name}")

        suite = suites[suite_name]
        benchmarks_to_run = benchmark_names if benchmark_names else suite["benchmarks"]

        results = []
        passed = 0
        failed = 0
        total_score = 0.0

        start_time = datetime.utcnow()

        for benchmark_name in benchmarks_to_run:
            result = await self._execute_single_benchmark(benchmark_name, context)
            results.append(result)

            if result.passed:
                passed += 1
            else:
                failed += 1

            total_score += result.score

        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        overall_score = total_score / len(benchmarks_to_run) if benchmarks_to_run else 0.0

        # Save results to database
        for result in results:
            await self.evaluation_repo.create_benchmark_result(result)

        return BenchmarkExecutionResult(
            suite_name=suite_name,
            total_benchmarks=len(benchmarks_to_run),
            passed=passed,
            failed=failed,
            overall_score=overall_score,
            duration_ms=duration_ms,
            results=results
        )

    async def _execute_single_benchmark(
        self,
        benchmark_name: str,
        context: dict[str, Any] | None = None
    ) -> BenchmarkResult:
        """
        Execute a single benchmark.

        Args:
            benchmark_name: Name of benchmark
            context: Execution context

        Returns:
            Benchmark result
        """
        import time
        from app.models.evaluation import BenchmarkResult

        start_time = time.time()

        # Execute benchmark based on name
        if benchmark_name == "memory_precision_test":
            score = await self.evaluation_repo.calculate_memory_precision()
            passed = score >= 0.8
        elif benchmark_name == "memory_recall_test":
            score = await self.evaluation_repo.calculate_memory_recall()
            passed = score >= 0.7
        elif benchmark_name == "case_leakage_test":
            score = 1.0 - await self.evaluation_repo.calculate_case_leakage()  # Invert for score
            passed = score >= 0.8
        elif benchmark_name == "policy_compliance_test":
            score = await self.evaluation_repo.calculate_policy_compliance()
            passed = score >= 0.9
        elif benchmark_name == "retrieval_drift_test":
            score = 1.0 - await self.evaluation_repo.calculate_retrieval_drift()  # Invert for score
            passed = score >= 0.8
        elif benchmark_name == "gatekeeper_accuracy_test":
            score = await self.evaluation_repo.calculate_gatekeeper_accuracy()
            passed = score >= 0.8
        elif benchmark_name == "repeated_failure_avoidance_test":
            score = await self.evaluation_repo.calculate_repeated_failure_avoidance()
            passed = score >= 0.7
        else:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        return BenchmarkResult(
            benchmark_name=benchmark_name,
            suite_name="manual",
            results={"score": score, "context": context or {}},
            passed=passed,
            score=score,
            duration_ms=duration_ms
        )

    async def get_evaluation_report(
        self,
        scope: str | None = None
    ) -> EvaluationReport:
        """
        Get latest evaluation report.

        Args:
            scope: Filter by scope

        Returns:
            Latest evaluation report
        """
        return await self.run_full_evaluation(scope)