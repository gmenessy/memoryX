"""
fRAG Models - Fragment Aware Retrieval Generation
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator
from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RetrievalSource(str, Enum):
    """Types of retrieval sources."""
    MEMORY_CARDS = "memory_cards"
    GRAPH = "graph"
    DOCUMENTS = "documents"
    POLICIES = "policies"
    DECISIONS = "decisions"
    EVENTS = "events"


class RetrievedFragment(BaseModel):
    """
    Single retrieved fragment with metadata.
    """
    fragment_id: UUID = Field(default_factory=uuid4, description="Unique fragment identifier")
    source_type: RetrievalSource = Field(..., description="Type of source")
    source_id: UUID = Field(..., description="Source entity ID")
    content: str = Field(..., description="Fragment content")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance score (0-1)")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score (0-1)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    ranking_position: int | None = Field(None, description="Position in ranking")


class RetrievalQuery(BaseModel):
    """
    Query for retrieval.
    """
    query: str = Field(..., description="Query text", min_length=1)
    query_type: str = Field(default="semantic", description="Type of query (semantic, keyword, hybrid)")
    scope: str | None = Field(None, description="Query scope/context")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to retrieve")
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum confidence threshold")
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional filters")


class RetrievalResult(BaseModel):
    """
    Result from retrieval operation.
    """
    query: str = Field(..., description="Original query")
    fragments: list[RetrievedFragment] = Field(default_factory=list, description="Retrieved fragments")
    total_fragments: int = Field(default=0, description="Total fragments found")
        retrieval_method: str = Field(..., description="Method used for retrieval")
    query_time_ms: float = Field(default=0.0, description="Query execution time in milliseconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RetrievalMetrics(BaseModel):
    """
    Metrics for retrieval performance.
    """
    precision_at_k: float = Field(default=0.0, ge=0.0, le=1.0, description="Precision at K")
    recall_at_k: float = Field(default=0.0, ge=0.0, le=1.0, description="Recall at K")
    mrr: float = Field(default=0.0, ge=0.0, le=1.0, description="Mean Reciprocal Rank")
    ndcg: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized Discounted Cumulative Gain")
    retrieval_time_ms: float = Field(default=0.0, description="Average retrieval time")
    cache_hit_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Cache hit rate")


class RetrievalOptimizationLogDB(Base):
    """
    SQLAlchemy Retrieval Optimization Log Model.
    Tracks retrieval performance for adaptive optimization.
    """
    __tablename__ = "retrieval_optimization_logs"

    log_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    retrieval_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    top_k: Mapped[int] = mapped_column(
        Float,
        nullable=False
    )
    fragments_retrieved: Mapped[int] = mapped_column(
        Float,
        nullable=False,
        default=0
    )
    fragments_used: Mapped[int] = mapped_column(
        Float,
        nullable=False,
        default=0
    )
    user_feedback: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )
    query_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    ranking_quality: Mapped[float] = mapped_column(
        Float,
        nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class RetrievalOptimizationLog(BaseModel):
    """
    Pydantic Retrieval Optimization Log Model.
    """
    log_id: UUID = Field(default_factory=uuid4, description="Unique log identifier")
    query: str = Field(..., description="Query that was executed")
    retrieval_method: str = Field(..., description="Retrieval method used")
    top_k: int = Field(..., description="Top K parameter")
    fragments_retrieved: int = Field(default=0, description="Number of fragments retrieved")
    fragments_used: int = Field(default=0, description="Number of fragments actually used")
    user_feedback: str | None = Field(None, description="User feedback (positive/negative/neutral)")
    query_time_ms: float = Field(..., description="Query execution time")
    ranking_quality: float | None = Field(None, ge=0.0, le=1.0, description="Quality of ranking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp")


class RetrievalOptimization(BaseModel):
    """
    Retrieval optimization parameters.
    """
    top_k: int = Field(default=10, ge=1, le=100, description="Top K results")
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum confidence")
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for semantic similarity")
    case_relevance_weight: float = Field(default=0.2, ge=0.0, le=1.0, description="Weight for case relevance")
    confidence_weight: float = Field(default=0.1, ge=0.0, le=1.0, description="Weight for confidence score")
    recency_weight: float = Field(default=0.05, ge=0.0, le=1.0, description="Weight for recency")
    trust_weight: float = Field(default=0.05, ge=0.0, le=1.0, description="Weight for trust score")

    @validator('top_k')
    def validate_top_k(cls, v):
        """Validate top_k is reasonable."""
        if v > 100:
            raise ValueError("Top K cannot exceed 100")
        if v < 1:
            raise ValueError("Top K must be at least 1")
        return v

    @validator('semantic_weight', 'case_relevance_weight', 'confidence_weight')
    def validate_weights(cls, v):
        """Validate individual weights."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Weights must be between 0.0 and 1.0")
        return v


class RetrievalFeedback(BaseModel):
    """
    User feedback for retrieval results.
    """
    query_id: UUID = Field(..., description="Query ID to provide feedback for")
    relevant_fragment_ids: list[UUID] = Field(default_factory=list, description="IDs of relevant fragments")
    irrelevant_fragment_ids: list[UUID] = Field(default_factory=list, description="IDs of irrelevant fragments")
    overall_rating: str = Field(..., description="Overall rating (positive/neutral/negative)")
    comments: str | None = Field(None, description="Additional comments")


# Retrieval methods as per specification
RETRIEVAL_METHODS = [
    "semantic",      # Semantic similarity search
    "keyword",       # Keyword-based search
    "hybrid",        # Hybrid semantic + keyword
    "graph",         # Graph-based traversal
    "vector",        # Vector similarity search
    "hybrid_rag"     # Hybrid RAG with multiple sources
]