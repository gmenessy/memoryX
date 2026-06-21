"""
fRAG Service - Business Logic Layer for Fragment Aware Retrieval
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.frag import (
    RetrievalQuery,
    RetrievalResult,
    RetrievedFragment,
    RetrievalFeedback,
    RetrievalOptimization,
    RetrievalMetrics,
    RetrievalOptimizationLog,
    RETRIEVAL_METHODS
)
from app.repositories.frag_repository import FRAGRepository


class FRAGService:
    """
    Service layer for Fragment Aware Retrieval Generation operations.
    Handles business logic for retrieval and optimization.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.frag_repo = FRAGRepository(session)

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """
        Perform retrieval operation.

        Args:
            query: Retrieval query

        Returns:
            Retrieval result with ranked fragments
        """
        # Validate query
        if not query.query.strip():
            raise ValueError("Query cannot be empty")

        if query.query_type not in RETRIEVAL_METHODS:
            raise ValueError(
                f"Invalid query type: {query.query_type}. "
                f"Must be one of: {', '.join(RETRIEVAL_METHODS)}"
            )

        # Get current optimization parameters
        optimization = await self.frag_repo.optimize_parameters()

        # Perform retrieval
        result = await self.frag_repo.retrieve(query, optimization)

        # Log retrieval for optimization
        await self.frag_repo.log_retrieval(
            query=query.query,
            retrieval_method=query.query_type,
            top_k=query.top_k,
            fragments_retrieved=result.metadata.get("total_candidates", 0),
            fragments_used=result.total_fragments,
            query_time_ms=result.query_time_ms
        )

        return result

    async def retrieve_with_optimization(
        self,
        query: RetrievalQuery,
        optimization: RetrievalOptimization
    ) -> RetrievalResult:
        """
        Perform retrieval with custom optimization parameters.

        Args:
            query: Retrieval query
            optimization: Custom optimization parameters

        Returns:
            Retrieval result with ranked fragments
        """
        # Validate query
        if not query.query.strip():
            raise ValueError("Query cannot be empty")

        # Convert optimization to dict
        opt_dict = optimization.dict()

        # Perform retrieval
        result = await self.frag_repo.retrieve(query, opt_dict)

        # Log retrieval
        await self.frag_repo.log_retrieval(
            query=query.query,
            retrieval_method=query.query_type,
            top_k=optimization.top_k,
            fragments_retrieved=result.metadata.get("total_candidates", 0),
            fragments_used=result.total_fragments,
            query_time_ms=result.query_time_ms
        )

        return result

    async def provide_feedback(
        self,
        feedback: RetrievalFeedback
    ) -> None:
        """
        Provide feedback for retrieval results.

        Args:
            feedback: User feedback
        """
        # Find the most recent log entry for this query
        from app.models.frag import RetrievalOptimizationLogDB
        from sqlalchemy import desc

        result = await self.session.execute(
            select(RetrievalOptimizationLogDB)
            .where(RetrievalOptimizationLogDB.query == feedback.query_id)
            .order_by(desc(RetrievalOptimizationLogDB.timestamp))
            .limit(1)
        )

        log_entry = result.scalar_one_or_none()

        if log_entry:
            # Update the log entry with feedback
            log_entry.user_feedback = feedback.overall_rating
            if feedback.overall_rating == "positive":
                log_entry.ranking_quality = 0.8
            elif feedback.overall_rating == "negative":
                log_entry.ranking_quality = 0.3
            else:
                log_entry.ranking_quality = 0.5

            await self.session.flush()

    async def get_retrieval_metrics(
        self,
        time_window_days: int = 7
    ) -> RetrievalMetrics:
        """
        Get retrieval performance metrics.

        Args:
            time_window_days: Time window for metrics

        Returns:
            Retrieval performance metrics
        """
        return await self.frag_repo.get_retrieval_metrics(time_window_days)

    async def get_optimization_parameters(
        self,
        time_window_days: int = 7
    ) -> dict[str, Any]:
        """
        Get current optimization parameters.

        Args:
            time_window_days: Time window for optimization

        Returns:
            Optimization parameters
        """
        return await self.frag_repo.optimize_parameters(time_window_days)

    async def adaptive_retrieve(
        self,
        query_text: str,
        scope: str | None = None,
        max_iterations: int = 3
    ) -> RetrievalResult:
        """
        Adaptive retrieval that automatically optimizes parameters.

        Args:
            query_text: Query text
            scope: Query scope
            max_iterations: Maximum optimization iterations

        Returns:
            Optimized retrieval result
        """
        # Start with default parameters
        query = RetrievalQuery(
            query=query_text,
            scope=scope,
            top_k=10,
            min_confidence=0.3
        )

        best_result = None
        best_score = 0.0

        for iteration in range(max_iterations):
            # Get current optimization parameters
            optimization = await self.frag_repo.optimize_parameters()

            # Perform retrieval
            result = await self.frag_repo.retrieve(query, optimization)

            # Calculate quality score
            quality_score = self._calculate_quality_score(result)

            if quality_score > best_score:
                best_result = result
                best_score = quality_score

            # If quality is good enough, stop
            if quality_score >= 0.8:
                break

            # Otherwise, adjust parameters and try again
            # (In a real implementation, this would be more sophisticated)

        return best_result or await self.retrieve(query)

    def _calculate_quality_score(self, result: RetrievalResult) -> float:
        """
        Calculate quality score for retrieval result.

        Args:
            result: Retrieval result

        Returns:
            Quality score (0-1)
        """
        if not result.fragments:
            return 0.0

        # Calculate average relevance
        avg_relevance = sum(f.relevance_score for f in result.fragments) / len(result.fragments)

        # Consider number of fragments retrieved
        fragment_score = min(result.total_fragments / 10.0, 1.0)

        # Consider query time (faster is better)
        time_score = max(0.0, 1.0 - (result.query_time_ms / 1000.0))

        # Combine scores
        quality = (
            avg_relevance * 0.7 +
            fragment_score * 0.2 +
            time_score * 0.1
        )

        return min(max(quality, 0.0), 1.0)