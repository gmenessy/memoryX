"""
fRAG Repository - Data Access Layer for Fragment Aware Retrieval
"""
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.frag import (
    RetrievalQuery,
    RetrievalResult,
    RetrievedFragment,
    RetrievalOptimizationLog,
    RetrievalOptimizationLogDB,
    RetrievalMetrics,
    RETRIEVAL_METHODS
)
from app.repositories.memory_repository import MemoryRepository
from app.repositories.graph_repository import GraphRepository


class FRAGRepository:
    """
    Repository for Fragment Aware Retrieval Generation operations.
    Handles retrieval from multiple sources with ranking and optimization.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.memory_repo = MemoryRepository(session)
        self.graph_repo = GraphRepository(session)
        self._vectorizer = None  # TF-IDF vectorizer cache

    async def retrieve(
        self,
        query: RetrievalQuery,
        optimization: dict[str, Any] | None = None
    ) -> RetrievalResult:
        """
        Perform retrieval operation.

        Args:
            query: Retrieval query
            optimization: Optimization parameters

        Returns:
            Retrieval result with ranked fragments
        """
        start_time = datetime.utcnow()

        # Get optimization parameters
        if optimization is None:
            optimization = {
                "top_k": query.top_k,
                "min_confidence": query.min_confidence,
                "semantic_weight": 0.7,
                "case_relevance_weight": 0.2,
                "confidence_weight": 0.1,
                "recency_weight": 0.05,
                "trust_weight": 0.05
            }

        # Collect fragments from different sources
        fragments = []

        # Search memory cards
        if query.filters.get("include_memories", True):
            memory_results = await self.memory_repo.search_memories(
                query=query.query,
                memory_type=query.filters.get("memory_type"),
                scope=query.scope,
                limit=query.top_k * 2  # Get more for reranking
            )

            for memory in memory_results:
                fragment = RetrievedFragment(
                    source_type="memory_cards",
                    source_id=memory.memory_id,
                    content=f"{memory.title}\n{memory.content}",
                    confidence=memory.confidence,
                    metadata={
                        "memory_type": memory.memory_type,
                        "scope": memory.scope,
                        "created_at": memory.created_at.isoformat(),
                        "updated_at": memory.updated_at.isoformat()
                    }
                )
                fragments.append(fragment)

        # Calculate scores
        scored_fragments = await self._rank_fragments(
            query.query,
            fragments,
            optimization
        )

        # Filter by minimum confidence and relevance
        filtered_fragments = [
            f for f in scored_fragments
            if f.confidence >= query.min_confidence and f.relevance_score >= query.min_confidence
        ]

        # Sort by final score and take top K
        # Final score = weighted combination
        for fragment in filtered_fragments:
            semantic_score = fragment.metadata.get("semantic_score", 0.0)
            case_score = fragment.metadata.get("case_relevance_score", 0.0)
            conf_score = fragment.confidence
            recency_score = fragment.metadata.get("recency_score", 0.0)
            trust_score = fragment.metadata.get("trust_score", 0.5)

            fragment.relevance_score = (
                semantic_score * optimization.get("semantic_weight", 0.7) +
                case_score * optimization.get("case_relevance_weight", 0.2) +
                conf_score * optimization.get("confidence_weight", 0.1) +
                recency_score * optimization.get("recency_weight", 0.05) +
                trust_score * optimization.get("trust_weight", 0.05)
            )

        # Sort by relevance score
        filtered_fragments.sort(key=lambda x: x.relevance_score, reverse=True)

        # Take top K
        top_fragments = filtered_fragments[:query.top_k]

        # Assign ranking positions
        for i, fragment in enumerate(top_fragments):
            fragment.ranking_position = i + 1

        query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return RetrievalResult(
            query=query.query,
            fragments=top_fragments,
            total_fragments=len(top_fragments),
            retrieval_method=query.query_type,
            query_time_ms=query_time_ms,
            metadata={
                "optimization_used": optimization,
                "total_candidates": len(fragments),
                "filtered_count": len(filtered_fragments)
            }
        )

    async def _rank_fragments(
        self,
        query: str,
        fragments: list[RetrievedFragment],
        optimization: dict[str, Any]
    ) -> list[RetrievedFragment]:
        """
        Rank fragments using multiple signals.

        Args:
            query: Query string
            fragments: List of fragments to rank
            optimization: Optimization parameters

        Returns:
            Ranked fragments
        """
        if not fragments:
            return []

        # Calculate semantic similarity
        semantic_scores = await self._calculate_semantic_similarity(query, fragments)

        # Calculate case relevance
        case_scores = await self._calculate_case_relevance(query, fragments)

        # Calculate recency scores
        recency_scores = self._calculate_recency_scores(fragments)

        # Combine scores
        for i, fragment in enumerate(fragments):
            fragment.metadata["semantic_score"] = semantic_scores[i]
            fragment.metadata["case_relevance_score"] = case_scores[i]
            fragment.metadata["recency_score"] = recency_scores[i]
            fragment.metadata["trust_score"] = fragment.metadata.get("trust_score", 0.5)

        return fragments

    async def _calculate_semantic_similarity(
        self,
        query: str,
        fragments: list[RetrievedFragment]
    ) -> list[float]:
        """
        Calculate semantic similarity using TF-IDF.

        Args:
            query: Query string
            fragments: List of fragments

        Returns:
            List of similarity scores
        """
        if not fragments:
            return []

        # Initialize vectorizer if needed
        if self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1
            )

        # Prepare texts
        texts = [query] + [f.content for f in fragments]

        # Calculate TF-IDF vectors
        try:
            tfidf_matrix = self._vectorizer.fit_transform(texts)

            # Calculate cosine similarity
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

            return similarities.tolist()

        except Exception:
            # Fallback to equal scores if vectorization fails
            return [0.5] * len(fragments)

    async def _calculate_case_relevance(
        self,
        query: str,
        fragments: list[RetrievedFragment]
    ) -> list[float]:
        """
        Calculate case relevance based on scope matching.

        Args:
            query: Query string
            fragments: List of fragments

        Returns:
            List of case relevance scores
        """
        scores = []

        for fragment in fragments:
            scope = fragment.metadata.get("scope", "")
            query_lower = query.lower()

            # Simple keyword matching in scope
            if scope and scope.lower() in query_lower:
                scores.append(0.8)
            elif scope and any(word in scope.lower() for word in query_lower.split()):
                scores.append(0.6)
            else:
                scores.append(0.3)

        return scores

    def _calculate_recency_scores(self, fragments: list[RetrievedFragment]) -> list[float]:
        """
        Calculate recency scores for fragments.

        Args:
            fragments: List of fragments

        Returns:
            List of recency scores
        """
        scores = []
        now = datetime.utcnow()

        for fragment in fragments:
            updated_at_str = fragment.metadata.get("updated_at")
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    days_old = (now - updated_at).days

                    # Decay over 90 days
                    recency_score = max(0.0, 1.0 - (days_old / 90.0))
                    scores.append(recency_score)
                except:
                    scores.append(0.5)
            else:
                scores.append(0.5)

        return scores

    async def log_retrieval(
        self,
        query: str,
        retrieval_method: str,
        top_k: int,
        fragments_retrieved: int,
        fragments_used: int,
        query_time_ms: float,
        user_feedback: str | None = None,
        ranking_quality: float | None = None
    ) -> RetrievalOptimizationLog:
        """
        Log retrieval operation for optimization.

        Args:
            query: Query that was executed
            retrieval_method: Method used
            top_k: Top K parameter
            fragments_retrieved: Number of fragments retrieved
            fragments_used: Number of fragments actually used
            query_time_ms: Query execution time
            user_feedback: User feedback
            ranking_quality: Quality of ranking

        Returns:
            Created log entry
        """
        log_db = RetrievalOptimizationLogDB(
            query=query,
            retrieval_method=retrieval_method,
            top_k=top_k,
            fragments_retrieved=fragments_retrieved,
            fragments_used=fragments_used,
            user_feedback=user_feedback,
            query_time_ms=query_time_ms,
            ranking_quality=ranking_quality
        )

        self.session.add(log_db)
        await self.session.flush()
        await self.session.refresh(log_db)

        return RetrievalOptimizationLog(
            log_id=log_db.log_id,
            query=log_db.query,
            retrieval_method=log_db.retrieval_method,
            top_k=log_db.top_k,
            fragments_retrieved=log_db.fragments_retrieved,
            fragments_used=log_db.fragments_used,
            user_feedback=log_db.user_feedback,
            query_time_ms=log_db.query_time_ms,
            ranking_quality=log_db.ranking_quality,
            timestamp=log_db.timestamp
        )

    async def get_retrieval_metrics(
        self,
        time_window_days: int = 7
    ) -> RetrievalMetrics:
        """
        Calculate retrieval performance metrics.

        Args:
            time_window_days: Time window for metrics calculation

        Returns:
            Retrieval performance metrics
        """
        from sqlalchemy import func, and_

        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)

        # Get recent logs
        result = await self.session.execute(
            select(RetrievalOptimizationLogDB).where(
                RetrievalOptimizationLogDB.timestamp >= cutoff_date
            )
        )
        logs = result.scalars().all()

        if not logs:
            return RetrievalMetrics()

        # Calculate metrics
        total_queries = len(logs)
        total_fragments_retrieved = sum(log.fragments_retrieved for log in logs)
        total_fragments_used = sum(log.fragments_used for log in logs)
        avg_query_time = sum(log.query_time_ms for log in logs) / total_queries

        # Calculate precision (fragments used / fragments retrieved)
        precision = (
            total_fragments_used / total_fragments_retrieved
            if total_fragments_retrieved > 0 else 0.0
        )

        # Calculate ranking quality from user feedback
        positive_feedback = sum(
            1 for log in logs
            if log.user_feedback == "positive"
        )
        ranking_quality = (
            positive_feedback / total_queries
            if total_queries > 0 else 0.0
        )

        return RetrievalMetrics(
            precision_at_k=precision,
            recall_at_k=0.8,  # Placeholder - would need ground truth
            mrr=ranking_quality,
            ndcg=ranking_quality,
            retrieval_time_ms=avg_query_time,
            cache_hit_rate=0.0  # Placeholder - cache not implemented yet
        )

    async def optimize_parameters(
        self,
        time_window_days: int = 7
    ) -> dict[str, Any]:
        """
        Optimize retrieval parameters based on recent performance.

        Args:
            time_window_days: Time window for optimization

        Returns:
            Optimized parameters
        """
        metrics = await self.get_retrieval_metrics(time_window_days)

        # Simple optimization logic
        optimized_params = {
            "top_k": 10,
            "min_confidence": 0.3,
            "semantic_weight": 0.7,
            "case_relevance_weight": 0.2,
            "confidence_weight": 0.1,
            "recency_weight": 0.05,
            "trust_weight": 0.05
        }

        # Adjust based on performance
        if metrics.precision_at_k < 0.5:
            # Low precision - increase confidence threshold
            optimized_params["min_confidence"] = 0.5
            optimized_params["confidence_weight"] = 0.2

        if metrics.retrieval_time_ms > 100:
            # Slow retrieval - reduce top_k
            optimized_params["top_k"] = 5

        if metrics.mrr < 0.6:
            # Poor ranking - increase semantic weight
            optimized_params["semantic_weight"] = 0.8
            optimized_params["case_relevance_weight"] = 0.1

        return optimized_params