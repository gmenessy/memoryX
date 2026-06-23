"""
Evaluation API Routes - REST Endpoints for Quality Metrics Operations
"""
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db_session
from app.models.evaluation import (
    EvaluationReport,
    BenchmarkExecutionRequest,
    BenchmarkExecutionResult,
    METRIC_TYPES
)
from app.services.evaluation_service import EvaluationService


class BenchmarkExecutionContext(BaseModel):
    """Context for benchmark execution."""
    benchmark_names: list[str] | None = None
    context: dict[str, Any] | None = None

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


@router.post("/evaluate", response_model=EvaluationReport)
async def run_evaluation(
    scope: str | None = Query(None, description="Evaluation scope"),
    session: AsyncSession = Depends(get_db_session)
) -> EvaluationReport:
    """
    Run comprehensive system evaluation.

    Calculates and records all quality metrics:
    - Memory Precision@K
    - Memory Recall@K
    - Case Leakage
    - Policy Compliance
    - Retrieval Drift
    - Gatekeeper Accuracy
    - Repeated Failure Avoidance

    Returns comprehensive evaluation report with scores, recommendations,
    and critical issues.
    """
    service = EvaluationService(session)
    return await service.run_full_evaluation(scope)


@router.get("/report", response_model=EvaluationReport)
async def get_evaluation_report(
    scope: str | None = Query(None, description="Report scope"),
    session: AsyncSession = Depends(get_db_session)
) -> EvaluationReport:
    """
    Get latest evaluation report.

    Returns the most recent evaluation report with all metrics
    and recommendations.
    """
    service = EvaluationService(session)
    return await service.get_evaluation_report(scope)


@router.post("/benchmark/{suite_name}", response_model=BenchmarkExecutionResult)
async def execute_benchmark_suite(
    suite_name: str,
    execution_context: BenchmarkExecutionContext = Body(None, description="Execution context"),
    session: AsyncSession = Depends(get_db_session)
) -> BenchmarkExecutionResult:
    """
    Execute a benchmark suite.

    Available suites:
    - **core_metrics**: Core system metrics (precision, recall, compliance)
    - **advanced_metrics**: Advanced metrics (leakage, drift, gatekeeper)
    - **full_evaluation**: Complete system evaluation

    Returns detailed results including individual benchmark scores,
    pass/fail status, and overall suite score.
    """
    try:
        service = EvaluationService(session)
        return await service.execute_benchmark_suite(
            suite_name=suite_name,
            benchmark_names=execution_context.benchmark_names if execution_context else None,
            context=execution_context.context if execution_context else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/metrics", response_model=dict)
async def get_available_metrics() -> dict:
    """
    Get available evaluation metrics.

    Returns the list of all quality metrics that are tracked.
    """
    return {
        "metrics": METRIC_TYPES,
        "descriptions": {
            "memory_precision": "Precision of memory retrieval (correctly_retrieved / total_retrieved)",
            "memory_recall": "Recall of memory retrieval (correctly_retrieved / total_relevant)",
            "case_leakage": "Cross-case memory leakage (lower is better)",
            "policy_compliance": "Compliance with governance policies",
            "retrieval_drift": "Degradation of retrieval quality over time (lower is better)",
            "gatekeeper_accuracy": "Accuracy of gatekeeper predictions",
            "repeated_failure_avoidance": "Avoidance of repeated mistakes"
        }
    }


@router.get("/suites", response_model=dict)
async def get_benchmark_suites() -> dict:
    """
    Get available benchmark suites.

    Returns the list of all available benchmark suites
    with their descriptions and requirements.
    """
    return {
        "suites": {
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
    }


@router.get("/health", response_model=dict)
async def get_system_health(
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get overall system health status.

    Returns a quick health check based on the latest evaluation metrics.
    """
    service = EvaluationService(session)
    report = await service.get_evaluation_report()

    # Determine health status
    if report.overall_score >= 0.8:
        status = "healthy"
    elif report.overall_score >= 0.6:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "overall_score": report.overall_score,
        "critical_issues": len(report.critical_issues),
        "performance_trend": report.performance_trend,
        "recommendations_count": len(report.recommendations)
    }