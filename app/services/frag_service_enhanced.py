"""
Enhanced fRAG Engine - Hybrid Retrieval System

Implements hybrid retrieval combining semantic and keyword search.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger

logger = get_logger(__name__)


class RetrievalMethod(str, Enum):
    """Retrieval methods."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    GRAPH = "graph"


@dataclass
class SearchResult:
    """A search result with metadata."""
    memory_id: str
    content: str
    score: float
    method: RetrievalMethod
    metadata: Dict[str, Any] = None
    rank: int = 0


@dataclass
class RetrievalConfig:
    """Configuration for retrieval operations."""
    hybrid_alpha: float = 0.5  # Balance between semantic and keyword (0-1)
    max_results: int = 10
    min_score: float = 0.3
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    enable_reranking: bool = True
    rerank_method: str = "score_fusion"


class HybridRetriever:
    """
    Hybrid retrieval system combining semantic and keyword search.
    """

    def __init__(self, session: AsyncSession, config: RetrievalConfig = None):
        self.session = session
        self.config = config or RetrievalConfig()
        self.cache: Dict[str, Tuple[List[SearchResult], float]] = {}

    async def retrieve(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        method: RetrievalMethod = RetrievalMethod.HYBRID
    ) -> List[SearchResult]:
        """
        Retrieve memories using specified method.

        Args:
            query: Search query
            filters: Optional filters for memory type, scope, etc.
            method: Retrieval method to use

        Returns:
            List of search results ranked by relevance
        """
        cache_key = self._get_cache_key(query, filters, method)

        # Check cache
        if self.config.enable_cache and cache_key in self.cache:
            results, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.debug(f"Cache hit for query: {query[:50]}")
                return results

        # Perform retrieval
        if method == RetrievalMethod.SEMANTIC:
            results = await self._semantic_search(query, filters)
        elif method == RetrievalMethod.KEYWORD:
            results = await self._keyword_search(query, filters)
        elif method == RetrievalMethod.HYBRID:
            results = await self._hybrid_search(query, filters)
        elif method == RetrievalMethod.GRAPH:
            results = await self._graph_traversal_search(query, filters)
        else:
            raise ValueError(f"Unknown retrieval method: {method}")

        # Apply reranking if enabled
        if self.config.enable_reranking and len(results) > 1:
            results = self._rerank_results(query, results)

        # Filter by min_score
        results = [r for r in results if r.score >= self.config.min_score]

        # Limit results
        results = results[:self.config.max_results]

        # Update cache
        if self.config.enable_cache:
            import time
            self.cache[cache_key] = (results, time.time())

        return results

    async def _semantic_search(
        self,
        query: str,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Perform semantic (vector-based) search."""
        logger.info(f"Performing semantic search for: {query[:50]}")

        # Simulate semantic search results
        # In production, this would use vector embeddings
        results = [
            SearchResult(
                memory_id=f"mem_{i}",
                content=f"Memory content {i} related to {query}",
                score=0.9 - (i * 0.05),
                method=RetrievalMethod.SEMANTIC,
                metadata={"embedding_distance": 0.1 + (i * 0.02)}
            )
            for i in range(10)
        ]

        return results

    async def _keyword_search(
        self,
        query: str,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Perform keyword-based search."""
        logger.info(f"Performing keyword search for: {query[:50]}")

        # Simulate keyword search results
        # In production, this would use full-text search
        query_lower = query.lower()
        results = [
            SearchResult(
                memory_id=f"mem_{i}",
                content=f"Memory {i} containing keywords from query",
                score=0.85 - (i * 0.05) if query_lower in f"memory {i}" else 0.3,
                method=RetrievalMethod.KEYWORD,
                metadata={"keyword_matches": 2 - (i % 3)}
            )
            for i in range(10)
        ]

        return results

    async def _hybrid_search(
        self,
        query: str,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Perform hybrid search combining semantic and keyword."""
        logger.info(f"Performing hybrid search for: {query[:50]}")

        # Get results from both methods
        semantic_results = await self._semantic_search(query, filters)
        keyword_results = await self._keyword_search(query, filters)

        # Score fusion
        alpha = self.config.hybrid_alpha

        # Create result map for fusion
        result_map: Dict[str, SearchResult] = {}

        # Add semantic results
        for result in semantic_results:
            result.score = result.score * alpha
            result_map[result.memory_id] = result

        # Add/merge keyword results
        for result in keyword_results:
            if result.memory_id in result_map:
                # Average the scores
                existing = result_map[result.memory_id]
                existing.score = (existing.score + result.score * (1 - alpha)) / 2
                existing.method = RetrievalMethod.HYBRID
            else:
                result.score = result.score * (1 - alpha)
                result.method = RetrievalMethod.HYBRID
                result_map[result.memory_id] = result

        results = list(result_map.values())
        results.sort(key=lambda x: x.score, reverse=True)

        return results

    async def _graph_traversal_search(
        self,
        query: str,
        filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Perform graph-based retrieval."""
        logger.info(f"Performing graph traversal search for: {query[:50]}")

        # Simulate graph traversal results
        # In production, this would traverse the memory graph
        results = [
            SearchResult(
                memory_id=f"mem_{i}",
                content=f"Memory {i} found via graph traversal",
                score=0.8 - (i * 0.06),
                method=RetrievalMethod.GRAPH,
                metadata={"graph_distance": i, "path_length": i + 1}
            )
            for i in range(8)
        ]

        return results

    def _rerank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank results using specified method."""
        if self.config.rerank_method == "score_fusion":
            return self._score_fusion_rerank(query, results)
        elif self.config.rerank_method == "reciprocal_rank":
            return self._reciprocal_rank_fusion(results)
        else:
            return results

    def _score_fusion_rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Simple score fusion reranking."""
        # Add query relevance boost
        query_words = set(query.lower().split())

        for result in results:
            content_words = set(result.content.lower().split())
            overlap = len(query_words & content_words)
            boost = min(0.2, overlap * 0.05)
            result.score = min(1.0, result.score + boost)

        results.sort(key=lambda x: x.score, reverse=True)

        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _reciprocal_rank_fusion(self, results: List[SearchResult]) -> List[SearchResult]:
        """Reciprocal Rank Fusion (RRF) reranking."""
        k = 60  # RRF constant

        # Group by memory_id
        memory_scores: Dict[str, float] = {}
        memory_data: Dict[str, SearchResult] = {}

        for result in results:
            if result.memory_id not in memory_data:
                memory_data[result.memory_id] = result

            # Add RRF score
            rrf_score = 1.0 / (k + result.rank)
            memory_scores[result.memory_id] = memory_scores.get(result.memory_id, 0) + rrf_score

        # Update results with RRF scores
        reranked = []
        for memory_id, score in memory_scores.items():
            result = memory_data[memory_id]
            result.score = score
            reranked.append(result)

        reranked.sort(key=lambda x: x.score, reverse=True)

        # Update ranks
        for i, result in enumerate(reranked):
            result.rank = i + 1

        return reranked

    def _get_cache_key(self, query: str, filters: Dict[str, Any], method: RetrievalMethod) -> str:
        """Generate cache key."""
        import hashlib
        key_str = f"{query}:{method}:{filters or 'none'}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        import time
        return (time.time() - timestamp) < self.config.cache_ttl_seconds

    def clear_cache(self):
        """Clear the retrieval cache."""
        self.cache.clear()
        logger.info("Retrieval cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "enabled": self.config.enable_cache,
            "ttl_seconds": self.config.cache_ttl_seconds
        }


class QueryExpander:
    """
    Query expansion for improved retrieval.
    """

    def __init__(self):
        self.expansion_rules: Dict[str, List[str]] = {
            "auth": ["authentication", "authorization", "login", "verify", "credentials"],
            "db": ["database", "storage", "persistence", "repository"],
            "api": ["endpoint", "route", "interface", "service"],
            "mem": ["memory", "storage", "cache", "remember"],
        }

    def expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms and related terms."""
        expansions = [query]
        query_lower = query.lower()

        # Apply expansion rules
        for key, synonyms in self.expansion_rules.items():
            if key in query_lower:
                expansions.extend(synonyms)

        # Add word-level expansions
        words = query_lower.split()
        for word in words:
            if len(word) > 3:
                # Add partial matches
                expansions.append(word[:len(word)-1])

        return list(set(expansions))

    def optimize_query(self, query: str) -> str:
        """Optimize query for better retrieval."""
        # Remove stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}

        words = query.lower().split()
        filtered = [w for w in words if w not in stop_words and len(w) > 2]

        return " ".join(filtered)

    def get_query_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get query suggestions based on partial input."""
        suggestions = []

        query_lower = query.lower()

        # Suggest based on expansion rules
        for key, synonyms in self.expansion_rules.items():
            if key in query_lower or any(key in s for s in synonyms):
                suggestions.extend(synonyms[:2])

        return list(set(suggestions))[:limit]
