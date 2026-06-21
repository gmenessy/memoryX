"""
Evaluation Repository - Data Access Layer for Quality Metrics
"""
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import (
    EvaluationMetricDB,
    BenchmarkResultDB,
    EvaluationMetric,
    BenchmarkResult,
    EvaluationReport,
    METRIC_TYPES,
    calculate_metric_level
)


class EvaluationRepository:
    """
    Repository for Evaluation Layer operations.
    Manages quality metrics and benchmark results.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_metric(self, metric: EvaluationMetric) -> EvaluationMetric:
        """
        Create a new evaluation metric.

        Args:
            metric: Evaluation metric to create

        Returns:
            Created metric
        """
        metric_db = EvaluationMetricDB(
            metric_type=metric.metric_type.value,
            metric_value=metric.metric_value,
            metric_level=metric.metric_level.value,
            context=metric.context,
            scope=metric.scope
        )

        self.session.add(metric_db)
        await self.session.flush()
        await self.session.refresh(metric_db)

        return EvaluationMetric(
            metric_id=metric_db.metric_id,
            metric_type=metric_db.metric_type,
            metric_value=metric_db.metric_value,
            metric_level=metric_db.metric_level,
            context=metric_db.context,
            scope=metric_db.scope,
            timestamp=metric_db.timestamp
        )

    async def get_metrics(
        self,
        metric_type: str | None = None,
        scope: str | None = None,
        time_window_hours: int | None = None,
        limit: int = 100
    ) -> list[EvaluationMetric]:
        """
        Get evaluation metrics with optional filtering.

        Args:
            metric_type: Filter by metric type
            scope: Filter by scope
            time_window_hours: Only return metrics from last X hours
            limit: Maximum number of results

        Returns:
            List of metrics
        """
        query = select(EvaluationMetricDB)

        conditions = []
        if metric_type:
            conditions.append(EvaluationMetricDB.metric_type == metric_type)
        if scope:
            conditions.append(EvaluationMetricDB.scope == scope)
        if time_window_hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            conditions.append(EvaluationMetricDB.timestamp >= cutoff_time)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(EvaluationMetricDB.timestamp))
        query = query.limit(limit)

        result = await self.session.execute(query)
        metrics = result.scalars().all()

        return [
            EvaluationMetric(
                metric_id=m.metric_id,
                metric_type=m.metric_type,
                metric_value=m.metric_value,
                metric_level=m.metric_level,
                context=m.context,
                scope=m.scope,
                timestamp=m.timestamp
            )
            for m in metrics
        ]

    async def get_latest_metrics(self) -> dict[str, EvaluationMetric]:
        """
        Get the latest metric for each metric type.

        Returns:
            Dictionary mapping metric types to their latest values
        """
        latest_metrics = {}

        for metric_type in METRIC_TYPES:
            result = await self.session.execute(
                select(EvaluationMetricDB)
                .where(EvaluationMetricDB.metric_type == metric_type)
                .order_by(desc(EvaluationMetricDB.timestamp))
                .limit(1)
            )

            metric = result.scalar_one_or_none()
            if metric:
                latest_metrics[metric_type] = EvaluationMetric(
                    metric_id=metric.metric_id,
                    metric_type=metric.metric_type,
                    metric_value=metric.metric_value,
                    metric_level=metric.metric_level,
                    context=metric.context,
                    scope=metric.scope,
                    timestamp=metric.timestamp
                )

        return latest_metrics

    async def calculate_memory_precision(self, scope: str | None = None) -> float:
        """
        Calculate memory precision metric.

        Precision = correctly_retrieved / total_retrieved

        Args:
            scope: Filter by scope

        Returns:
            Precision score (0-1)
        """
        # This would typically involve analyzing retrieval logs
        # For now, return a placeholder value
        # In production, this would query retrieval optimization logs
        return 0.85

    async def calculate_memory_recall(self, scope: str | None = None) -> float:
        """
        Calculate memory recall metric.

        Recall = correctly_retrieved / total_relevant

        Args:
            scope: Filter by scope

        Returns:
            Recall score (0-1)
        """
        # Placeholder - would analyze retrieval logs in production
        return 0.78

    async def calculate_case_leakage(self, scope: str | None = None) -> float:
        """
        Calculate case leakage metric.

        Measures if memories from one case leak into another case's retrieval.

        Args:
            scope: Filter by scope

        Returns:
            Leakage score (0-1, lower is better)
        """
        # Placeholder - would analyze scope violations
        return 0.15

    async def calculate_policy_compliance(self, scope: str | None = None) -> float:
        """
        Calculate policy compliance metric.

        Measures how often actions comply with governance policies.

        Args:
            scope: Filter by scope

        Returns:
            Compliance score (0-1)
        """
        # Placeholder - would analyze gatekeeper logs
        return 0.92

    async def calculate_retrieval_drift(self, scope: str | None = None) -> float:
        """
        Calculate retrieval drift metric.

        Measures how much retrieval quality has degraded over time.

        Args:
            scope: Filter by scope

        Returns:
            Drift score (0-1, lower is better)
        """
        # Get recent retrieval metrics
        recent_metrics = await self.get_metrics(
            metric_type="retrieval_quality",
            scope=scope,
            time_window_hours=24
        )

        if len(recent_metrics) < 2:
            return 0.0  # Not enough data

        # Calculate drift as difference from baseline
        latest = recent_metrics[0].metric_value
        baseline = recent_metrics[-1].metric_value

        drift = abs(latest - baseline)
        return drift

    async def calculate_gatekeeper_accuracy(self, scope: str | None = None) -> float:
        """
        Calculate gatekeeper accuracy metric.

        Measures how often gatekeeper predictions are correct.

        Args:
            scope: Filter by scope

        Returns:
            Accuracy score (0-1)
        """
        # Placeholder - would analyze gatekeeper feedback
        return 0.88

    async def calculate_repeated_failure_avoidance(self, scope: str | None = None) -> float:
        """
        Calculate repeated failure avoidance metric.

        Measures how often the system avoids making the same mistakes.

        Args:
            scope: Filter by scope

        Returns:
            Avoidance score (0-1)
        """
        # Placeholder - would analyze failure patterns
        return 0.75

    async def create_benchmark_result(self, result: BenchmarkResult) -> BenchmarkResult:
        """
        Create a new benchmark result.

        Args:
            result: Benchmark result to create

        Returns:
            Created benchmark result
        """
        result_db = BenchmarkResultDB(
            benchmark_name=result.benchmark_name,
            suite_name=result.suite_name,
            results=result.results,
            passed=result.passed,
            score=result.score,
            duration_ms=result.duration_ms
        )

        self.session.add(result_db)
        await self.session.flush()
        await self.session.refresh(result_db)

        return BenchmarkResult(
            benchmark_id=result_db.benchmark_id,
            benchmark_name=result_db.benchmark_name,
            suite_name=result_db.suite_name,
            results=result_db.results,
            passed=result_db.passed,
            score=result_db.score,
            duration_ms=result_db.duration_ms,
            timestamp=result_db.timestamp
        )

    async def get_benchmark_results(
        self,
        suite_name: str | None = None,
        limit: int = 100
    ) -> list[BenchmarkResult]:
        """
        Get benchmark results with optional filtering.

        Args:
            suite_name: Filter by suite name
            limit: Maximum number of results

        Returns:
            List of benchmark results
        """
        query = select(BenchmarkResultDB)

        if suite_name:
            query = query.where(BenchmarkResultDB.suite_name == suite_name)

        query = query.order_by(desc(BenchmarkResultDB.timestamp))
        query = query.limit(limit)

        result = await self.session.execute(query)
        benchmarks = result.scalars().all()

        return [
            BenchmarkResult(
                benchmark_id=b.benchmark_id,
                benchmark_name=b.benchmark_name,
                suite_name=b.suite_name,
                results=b.results,
                passed=b.passed,
                score=b.score,
                duration_ms=b.duration_ms,
                timestamp=b.timestamp
            )
            for b in benchmarks
        ]