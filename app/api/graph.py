"""
Graph API Routes - REST Endpoints for Memory Graph Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.graph import (
    GraphNodeCreate,
    GraphEdgeCreate,
    GraphNodeResponse,
    GraphEdgeResponse,
    GraphTraversalResult,
    GraphStatistics,
    NODE_TYPES,
    EDGE_TYPES
)
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.post("/nodes", response_model=GraphNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_graph_node(
    node_data: GraphNodeCreate,
    session: AsyncSession = Depends(get_db_session)
) -> GraphNodeResponse:
    """
    Create a new graph node.

    Graph nodes represent entities in the knowledge graph.
    Each node is linked to an external entity (memory, event, etc.).

    - **node_type**: Type of node (memory, event, document, etc.)
    - **external_id**: External entity ID
    - **label**: Node label
    - **properties**: Additional properties
    """
    try:
        service = GraphService(session)
        return await service.create_node(node_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/nodes/{node_id}", response_model=GraphNodeResponse)
async def get_graph_node(
    node_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> GraphNodeResponse:
    """
    Get a specific graph node by ID.
    """
    service = GraphService(session)
    node = await service.get_node(node_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph node {node_id} not found"
        )

    return node


@router.get("/nodes", response_model=list[GraphNodeResponse])
async def list_graph_nodes(
    node_type: str | None = Query(None, description="Filter by node type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[GraphNodeResponse]:
    """
    List graph nodes with optional filtering.

    Results are ordered by created_at (newest first).
    """
    service = GraphService(session)
    return await service.list_nodes(node_type, limit, offset)


@router.post("/edges", response_model=GraphEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_graph_edge(
    edge_data: GraphEdgeCreate,
    session: AsyncSession = Depends(get_db_session)
) -> GraphEdgeResponse:
    """
    Create a new graph edge (relationship).

    Graph edges represent relationships between nodes.
    Each edge has a type (references, supports, contradicts, etc.).

    - **source_node**: Source node ID
    - **target_node**: Target node ID
    - **edge_type**: Type of relationship
    - **weight**: Relationship strength (0-1)
    - **properties**: Additional properties
    """
    try:
        service = GraphService(session)
        return await service.create_edge(edge_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/edges/{edge_id}", response_model=GraphEdgeResponse)
async def get_graph_edge(
    edge_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> GraphEdgeResponse:
    """
    Get a specific graph edge by ID.
    """
    service = GraphService(session)
    edge = await service.get_edge(edge_id)

    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph edge {edge_id} not found"
        )

    return edge


@router.get("/edges", response_model=list[GraphEdgeResponse])
async def list_graph_edges(
    source_node: UUID | None = Query(None, description="Filter by source node"),
    target_node: UUID | None = Query(None, description="Filter by target node"),
    edge_type: str | None = Query(None, description="Filter by edge type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[GraphEdgeResponse]:
    """
    List graph edges with optional filtering.

    Results are ordered by created_at (newest first).
    """
    service = GraphService(session)
    return await service.list_edges(source_node, target_node, edge_type, limit, offset)


@router.get("/nodes/{node_id}/neighbors", response_model=list[GraphNodeResponse])
async def get_node_neighbors(
    node_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> list[GraphNodeResponse]:
    """
    Get neighboring nodes.

    Returns all nodes directly connected to the specified node.
    """
    try:
        service = GraphService(session)
        return await service.get_neighbors(node_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/path/{source_id}/{target_id}", response_model=GraphTraversalResult)
async def find_shortest_path(
    source_id: UUID,
    target_id: UUID,
    max_depth: int = Query(5, ge=1, le=10, description="Maximum path depth"),
    session: AsyncSession = Depends(get_db_session)
) -> GraphTraversalResult:
    """
    Find shortest path between two nodes.

    Returns the shortest path including nodes and edges.
    Useful for understanding relationships between entities.
    """
    try:
        service = GraphService(session)
        result = await service.find_shortest_path(source_id, target_id, max_depth)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No path found between nodes {source_id} and {target_id}"
            )

        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/nodes/{node_id}/related", response_model=list[GraphNodeResponse])
async def find_related_nodes(
    node_id: UUID,
    max_distance: int = Query(2, ge=1, le=5, description="Maximum graph distance"),
    max_results: int = Query(50, ge=1, le=100, description="Maximum results"),
    session: AsyncSession = Depends(get_db_session)
) -> list[GraphNodeResponse]:
    """
    Find nodes related to a given node.

    Returns all nodes within the specified graph distance.
    Results are ordered by distance (closest first).
    """
    try:
        service = GraphService(session)
        return await service.find_related_nodes(node_id, max_distance, max_results)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/statistics", response_model=GraphStatistics)
async def get_graph_statistics(
    session: AsyncSession = Depends(get_db_session)
) -> GraphStatistics:
    """
    Get graph statistics.

    Returns comprehensive statistics about the knowledge graph.
    """
    service = GraphService(session)
    return await service.get_graph_statistics()


@router.get("/node-types", response_model=list[str])
async def list_node_types() -> list[str]:
    """
    Get available node types.

    Returns the list of valid node types according to the specification.
    """
    return NODE_TYPES


@router.get("/edge-types", response_model=list[str])
async def list_edge_types() -> list[str]:
    """
    Get available edge types.

    Returns the list of valid edge types according to the specification.
    """
    return EDGE_TYPES