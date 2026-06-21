"""
Memory Graph Models - Knowledge Relationships Storage
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator
from sqlalchemy import DateTime, JSON, String, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NodeType(str, Enum):
    """Types of nodes in the memory graph."""
    MEMORY = "memory"
    DOCUMENT = "document"
    DECISION = "decision"
    RULE = "rule"
    CASE = "case"
    PERSON = "person"
    SKILL = "skill"
    POLICY = "policy"
    EVENT = "event"


class EdgeType(str, Enum):
    """Types of relationships (edges) in the memory graph."""
    REFERENCES = "references"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    DERIVED_FROM = "derived_from"
    BELONGS_TO = "belongs_to"
    CAUSED_BY = "caused_by"
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    PRECEDES = "precedes"
    IMPLEMENTS = "implements"


class GraphNodeDB(Base):
    """
    SQLAlchemy Graph Node Model - Database representation.
    Represents entities in the memory graph.
    """
    __tablename__ = "graph_nodes"

    node_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    node_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    external_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
        unique=True
    )
    label: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    edges_as_source = relationship("GraphEdgeDB", foreign_keys="GraphEdgeDB.source_node", back_populates="source_node_obj")
    edges_as_target = relationship("GraphEdgeDB", foreign_keys="GraphEdgeDB.target_node", back_populates="target_node_obj")


class GraphEdgeDB(Base):
    """
    SQLAlchemy Graph Edge Model - Database representation.
    Represents relationships between nodes in the memory graph.
    """
    __tablename__ = "graph_edges"

    edge_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    source_node: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("graph_nodes.node_id"),
        nullable=False,
        index=True
    )
    target_node: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("graph_nodes.node_id"),
        nullable=False,
        index=True
    )
    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0
    )
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    source_node_obj = relationship("GraphNodeDB", foreign_keys=[source_node], back_populates="edges_as_source")
    target_node_obj = relationship("GraphNodeDB", foreign_keys=[target_node], back_populates="edges_as_target")


class GraphNode(BaseModel):
    """
    Pydantic Graph Node Model - API representation.
    """
    node_id: UUID = Field(default_factory=uuid4, description="Unique node identifier")
    node_type: NodeType = Field(..., description="Type of node")
    external_id: UUID = Field(..., description="External entity ID (memory_id, event_id, etc.)")
    label: str = Field(..., description="Node label", min_length=1, max_length=500)
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional node properties")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @validator('label')
    def validate_label(cls, v):
        """Validate label is not empty."""
        if not v.strip():
            raise ValueError("Label cannot be empty")
        return v.strip()


class GraphEdge(BaseModel):
    """
    Pydantic Graph Edge Model - API representation.
    """
    edge_id: UUID = Field(default_factory=uuid4, description="Unique edge identifier")
    source_node: UUID = Field(..., description="Source node ID")
    target_node: UUID = Field(..., description="Target node ID")
    edge_type: EdgeType = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship weight (0-1)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional edge properties")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @validator('weight')
    def validate_weight(cls, v):
        """Validate weight is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")
        return v


class GraphNodeCreate(BaseModel):
    """Graph Node Creation Schema."""
    node_type: NodeType = Field(..., description="Type of node")
    external_id: UUID = Field(..., description="External entity ID")
    label: str = Field(..., description="Node label", min_length=1, max_length=500)
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class GraphEdgeCreate(BaseModel):
    """Graph Edge Creation Schema."""
    source_node: UUID = Field(..., description="Source node ID")
    target_node: UUID = Field(..., description="Target node ID")
    edge_type: EdgeType = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship weight")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class GraphNodeResponse(BaseModel):
    """Graph Node Response Schema."""
    node_id: UUID
    node_type: str
    external_id: UUID
    label: str
    properties: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GraphEdgeResponse(BaseModel):
    """Graph Edge Response Schema."""
    edge_id: UUID
    source_node: UUID
    target_node: UUID
    edge_type: str
    weight: float
    properties: dict[str, Any]
    created_at: datetime


class GraphTraversalResult(BaseModel):
    """Graph Traversal Result."""
    path: list[UUID] = Field(default_factory=list, description="Path of node IDs")
    nodes: list[GraphNodeResponse] = Field(default_factory=list, description="Nodes in the path")
    edges: list[GraphEdgeResponse] = Field(default_factory=list, description="Edges in the path")
    total_weight: float = Field(default=0.0, description="Total path weight")
    length: int = Field(default=0, description="Path length (number of edges)")


class GraphStatistics(BaseModel):
    """Graph Statistics."""
    total_nodes: int = Field(..., description="Total number of nodes")
    total_edges: int = Field(..., description="Total number of edges")
    nodes_by_type: dict[str, int] = Field(default_factory=dict, description="Nodes count by type")
    edges_by_type: dict[str, int] = Field(default_factory=dict, description="Edges count by type")
    connected_components: int = Field(default=0, description="Number of connected components")
    average_degree: float = Field(default=0.0, description="Average node degree")


# Node and Edge types for easy reference
NODE_TYPES = [node_type.value for node_type in NodeType]
EDGE_TYPES = [edge_type.value for edge_type in EdgeType]