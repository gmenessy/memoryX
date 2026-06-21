"""
fRAG API Routes - REST Endpoints for Fragment Aware Retrieval Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.frag import (
    RetrievalQuery,
    RetrievalResult,
    RetrievalFeedback,
    RetrievalOptimization,
    RetrievalMetrics,
    RETRIEVAL_METHODS
)
from app.services.frag_service import FRAGService

router = APIRouter(prefix="/api/frag", tags=["fRAG"])


@router.post("/retrieve", response_model=RetrievalResult)
async def retrieve_fragments(
    query: RetrievalQuery,
    session: AsyncSession = Depends(get_db_session)
) -> RetrievalResult:
    """
    Retrieve fragments using fRAG (Fragment Aware Retrieval Generation).

    This endpoint performs intelligent retrieval from multiple sources
    (memory cards, graph, documents, etc.) with advanced ranking.

    - **query**: Query text for retrieval
    - **query_type**: Type of retrieval (semantic, keyword, hybrid, etc.)
    - **scope**: Optional scope/context for the query
    - **top_k**: Number of results to return (1-100)
    - **min_confidence**: Minimum confidence threshold (0-1)
    - **filters**: Additional filters

    Returns ranked fragments with relevance scores and metadata.
    """
    try:
        service = FRAGService(session)
        return await service.retrieve(query)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/retrieve/optimized", response_model=RetrievalResult)
async def retrieve_with_optimization(
    query: RetrievalQuery,
    optimization: RetrievalOptimization,
    session: AsyncSession = Depends(get_db_session)
) -> RetrievalResult:
    """
    Retrieve fragments with custom optimization parameters.

    Allows fine-tuning of retrieval behavior with custom weights
    for different scoring components.

    - **query**: Retrieval query
    - **optimization**: Custom optimization parameters
    """
    try:
        service = FRAGService(session)
        return await service.retrieve_with_optimization(query, optimization)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/retrieve/adaptive", response_model=RetrievalResult)
async def adaptive_retrieve(
    query_text: str = Query(..., min_length=1, description="Query text"),
    scope: str | None = Query(None, description="Query scope"),
    max_iterations: int = Query(3, ge=1, le=5, description="Maximum optimization iterations"),
    session: AsyncSession = Depends(get_db_session)
) -> RetrievalResult:
    """
    Adaptive retrieval with automatic parameter optimization.

    Automatically adjusts retrieval parameters based on historical
    performance and current results to maximize quality.
    """
    try:
        service = FRAGService(session)
        return await service.adaptive_retrieve(query_text, scope, max_iterations)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def provide_retrieval_feedback(
    feedback: RetrievalFeedback,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Provide feedback for retrieval results.

    User feedback is used to optimize future retrieval operations.
    Helps the system learn what constitutes good results.

    - **query_id**: Query ID to provide feedback for
    - **relevant_fragment_ids**: IDs of relevant fragments
    - **irrelevant_fragment_ids**: IDs of irrelevant fragments
    - **overall_rating**: Overall rating (positive/neutral/negative)
    - **comments**: Additional comments
    """
    service = FRAGService(session)
    await service.provide_feedback(feedback)


@router.get("/metrics", response_model=RetrievalMetrics)
async def get_retrieval_metrics(
    time_window_days: int = Query(7, ge=1, le=90, description="Time window in days"),
    session: AsyncSession = Depends(get_db_session)
) -> RetrievalMetrics:
    """
    Get retrieval performance metrics.

    Returns comprehensive metrics about retrieval performance
    including precision, recall, MRR, NDCG, and query times.
    """
    service = FRAGService(session)
    return await service.get_retrieval_metrics(time_window_days)


@router.get("/optimization", response_model=dict)
async def get_optimization_parameters(
    time_window_days: int = Query(7, ge=1, le=90, description="Time window in days"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get current optimization parameters.

    Returns the current adaptive optimization parameters
    based on recent retrieval performance.
    """
    service = FRAGService(session)
    return await service.get_optimization_parameters(time_window_days)


@router.get("/methods", response_model=list[str])
async def list_retrieval_methods() -> list[str]:
    """
    Get available retrieval methods.

    Returns the list of valid retrieval methods.
    """
    return RETRIEVAL_METHODS