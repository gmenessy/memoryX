"""
Memory Graph Repository - Data Access Layer for Memory Graph
"""
from typing import Any, Optional
from uuid import UUID
import networkx as nx

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph import (
    GraphNodeDB,
    GraphEdgeDB,
    GraphNodeCreate,
    GraphEdgeCreate,
    GraphNodeResponse,
    GraphEdgeResponse,
    GraphTraversalResult,
    GraphStatistics
)


class GraphRepository:
    """
    Repository for Memory Graph operations.
    Manages knowledge relationships using NetworkX and SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._nx_graph = None  # NetworkX graph instance

    async def create_node(self, node_data: GraphNodeCreate) -> GraphNodeResponse:
        """
        Create a new graph node.

        Args:
            node_data: Node creation data

        Returns:
            Created node response
        """
        node_db = GraphNodeDB(
            node_type=node_data.node_type.value,
            external_id=node_data.external_id,
            label=node_data.label,
            properties=node_data.properties
        )

        self.session.add(node_db)
        await self.session.flush()
        await self.session.refresh(node_db)

        # Invalidate NetworkX graph cache
        self._nx_graph = None

        return GraphNodeResponse(
            node_id=node_db.node_id,
            node_type=node_db.node_type,
            external_id=node_db.external_id,
            label=node_db.label,
            properties=node_db.properties,
            created_at=node_db.created_at,
            updated_at=node_db.updated_at
        )

    async def get_node(self, node_id: UUID) -> GraphNodeResponse | None:
        """
        Get node by ID.

        Args:
            node_id: Node UUID

        Returns:
            Node response or None if not found
        """
        result = await self.session.execute(
            select(GraphNodeDB).where(GraphNodeDB.node_id == node_id)
        )
        node_db = result.scalar_one_or_none()

        if not node_db:
            return None

        return GraphNodeResponse(
            node_id=node_db.node_id,
            node_type=node_db.node_type,
            external_id=node_db.external_id,
            label=node_db.label,
            properties=node_db.properties,
            created_at=node_db.created_at,
            updated_at=node_db.updated_at
        )

    async def get_node_by_external_id(self, external_id: UUID) -> GraphNodeResponse | None:
        """
        Get node by external ID.

        Args:
            external_id: External entity ID

        Returns:
            Node response or None if not found
        """
        result = await self.session.execute(
            select(GraphNodeDB).where(GraphNodeDB.external_id == external_id)
        )
        node_db = result.scalar_one_or_none()

        if not node_db:
            return None

        return GraphNodeResponse(
            node_id=node_db.node_id,
            node_type=node_db.node_type,
            external_id=node_db.external_id,
            label=node_db.label,
            properties=node_db.properties,
            created_at=node_db.created_at,
            updated_at=node_db.updated_at
        )

    async def list_nodes(
        self,
        node_type: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphNodeResponse]:
        """
        List nodes with optional filtering.

        Args:
            node_type: Filter by node type
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of nodes
        """
        query = select(GraphNodeDB)

        if node_type:
            query = query.where(GraphNodeDB.node_type == node_type)

        query = query.order_by(GraphNodeDB.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        nodes = result.scalars().all()

        return [
            GraphNodeResponse(
                node_id=node.node_id,
                node_type=node.node_type,
                external_id=node.external_id,
                label=node.label,
                properties=node.properties,
                created_at=node.created_at,
                updated_at=node.updated_at
            )
            for node in nodes
        ]

    async def create_edge(self, edge_data: GraphEdgeCreate) -> GraphEdgeResponse:
        """
        Create a new graph edge.

        Args:
            edge_data: Edge creation data

        Returns:
            Created edge response
        """
        # Verify nodes exist
        source = await self.get_node(edge_data.source_node)
        target = await self.get_node(edge_data.target_node)

        if not source:
            raise ValueError(f"Source node {edge_data.source_node} not found")
        if not target:
            raise ValueError(f"Target node {edge_data.target_node} not found")

        edge_db = GraphEdgeDB(
            source_node=edge_data.source_node,
            target_node=edge_data.target_node,
            edge_type=edge_data.edge_type.value,
            weight=edge_data.weight,
            properties=edge_data.properties
        )

        self.session.add(edge_db)
        await self.session.flush()
        await self.session.refresh(edge_db)

        # Invalidate NetworkX graph cache
        self._nx_graph = None

        return GraphEdgeResponse(
            edge_id=edge_db.edge_id,
            source_node=edge_db.source_node,
            target_node=edge_db.target_node,
            edge_type=edge_db.edge_type,
            weight=edge_db.weight,
            properties=edge_db.properties,
            created_at=edge_db.created_at
        )

    async def get_edge(self, edge_id: UUID) -> GraphEdgeResponse | None:
        """
        Get edge by ID.

        Args:
            edge_id: Edge UUID

        Returns:
            Edge response or None if not found
        """
        result = await self.session.execute(
            select(GraphEdgeDB).where(GraphEdgeDB.edge_id == edge_id)
        )
        edge_db = result.scalar_one_or_none()

        if not edge_db:
            return None

        return GraphEdgeResponse(
            edge_id=edge_db.edge_id,
            source_node=edge_db.source_node,
            target_node=edge_db.target_node,
            edge_type=edge_db.edge_type,
            weight=edge_db.weight,
            properties=edge_db.properties,
            created_at=edge_db.created_at
        )

    async def list_edges(
        self,
        source_node: UUID | None = None,
        target_node: UUID | None = None,
        edge_type: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphEdgeResponse]:
        """
        List edges with optional filtering.

        Args:
            source_node: Filter by source node
            target_node: Filter by target node
            edge_type: Filter by edge type
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of edges
        """
        query = select(GraphEdgeDB)

        conditions = []
        if source_node:
            conditions.append(GraphEdgeDB.source_node == source_node)
        if target_node:
            conditions.append(GraphEdgeDB.target_node == target_node)
        if edge_type:
            conditions.append(GraphEdgeDB.edge_type == edge_type)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(GraphEdgeDB.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        edges = result.scalars().all()

        return [
            GraphEdgeResponse(
                edge_id=edge.edge_id,
                source_node=edge.source_node,
                target_node=edge.target_node,
                edge_type=edge.edge_type,
                weight=edge.weight,
                properties=edge.properties,
                created_at=edge.created_at
            )
            for edge in edges
        ]

    async def get_neighbors(self, node_id: UUID) -> list[GraphNodeResponse]:
        """
        Get neighboring nodes.

        Args:
            node_id: Node ID

        Returns:
            List of neighboring nodes
        """
        # Get outgoing edges
        outgoing_result = await self.session.execute(
            select(GraphEdgeDB).where(GraphEdgeDB.source_node == node_id)
        )
        outgoing_edges = outgoing_result.scalars().all()

        neighbor_ids = [edge.target_node for edge in outgoing_edges]

        if not neighbor_ids:
            return []

        # Get neighbor nodes
        result = await self.session.execute(
            select(GraphNodeDB).where(GraphNodeDB.node_id.in_(neighbor_ids))
        )
        nodes = result.scalars().all()

        return [
            GraphNodeResponse(
                node_id=node.node_id,
                node_type=node.node_type,
                external_id=node.external_id,
                label=node.label,
                properties=node.properties,
                created_at=node.created_at,
                updated_at=node.updated_at
            )
            for node in nodes
        ]

    async def find_shortest_path(
        self,
        source_id: UUID,
        target_id: UUID,
        max_depth: int = 5
    ) -> GraphTraversalResult | None:
        """
        Find shortest path between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_depth: Maximum path length

        Returns:
            Path result or None if no path found
        """
        graph = await self._get_networkx_graph()

        try:
            # Find shortest path using NetworkX
            path = nx.shortest_path(graph, source=source_id, target=target_id)

            # Limit path length
            if len(path) > max_depth + 1:  # +1 because path includes both endpoints
                return None

            # Get nodes and edges in path
            nodes = []
            edges = []
            total_weight = 0.0

            for node_id in path:
                node = await self.get_node(node_id)
                if node:
                    nodes.append(node)

            # Get edges between consecutive nodes
            for i in range(len(path) - 1):
                edge_result = await self.session.execute(
                    select(GraphEdgeDB).where(
                        and_(
                            GraphEdgeDB.source_node == path[i],
                            GraphEdgeDB.target_node == path[i + 1]
                        )
                    )
                )
                edge = edge_result.scalar_one_or_none()
                if edge:
                    edges.append(GraphEdgeResponse(
                        edge_id=edge.edge_id,
                        source_node=edge.source_node,
                        target_node=edge.target_node,
                        edge_type=edge.edge_type,
                        weight=edge.weight,
                        properties=edge.properties,
                        created_at=edge.created_at
                    ))
                    total_weight += edge.weight

            return GraphTraversalResult(
                path=path,
                nodes=nodes,
                edges=edges,
                total_weight=total_weight,
                length=len(edges)
            )

        except nx.NetworkXNoPath:
            return None

    async def find_connected_components(self) -> list[list[UUID]]:
        """
        Find connected components in the graph.

        Returns:
            List of connected components (each is a list of node IDs)
        """
        graph = await self._get_networkx_graph()
        return list(nx.connected_components(graph))

    async def get_graph_statistics(self) -> GraphStatistics:
        """
        Get graph statistics.

        Returns:
            Graph statistics
        """
        # Count nodes
        node_result = await self.session.execute(select(GraphNodeDB))
        nodes = node_result.scalars().all()
        total_nodes = len(nodes)

        # Count edges
        edge_result = await self.session.execute(select(GraphEdgeDB))
        edges = edge_result.scalars().all()
        total_edges = len(edges)

        # Count nodes by type
        nodes_by_type = {}
        for node in nodes:
            nodes_by_type[node.node_type] = nodes_by_type.get(node.node_type, 0) + 1

        # Count edges by type
        edges_by_type = {}
        for edge in edges:
            edges_by_type[edge.edge_type] = edges_by_type.get(edge.edge_type, 0) + 1

        # Calculate connected components and average degree
        if total_nodes > 0:
            graph = await self._get_networkx_graph()
            connected_components = nx.number_connected_components(graph)
            average_degree = total_edges * 2 / total_nodes if total_nodes > 0 else 0.0
        else:
            connected_components = 0
            average_degree = 0.0

        return GraphStatistics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            nodes_by_type=nodes_by_type,
            edges_by_type=edges_by_type,
            connected_components=connected_components,
            average_degree=average_degree
        )

    async def _get_networkx_graph(self) -> nx.Graph:
        """
        Build and cache NetworkX graph from database.

        Returns:
            NetworkX Graph instance
        """
        if self._nx_graph is not None:
            return self._nx_graph

        # Create new graph
        graph = nx.Graph()

        # Add nodes
        node_result = await self.session.execute(select(GraphNodeDB))
        nodes = node_result.scalars().all()

        for node in nodes:
            graph.add_node(node.node_id, **node.properties)

        # Add edges
        edge_result = await self.session.execute(select(GraphEdgeDB))
        edges = edge_result.scalars().all()

        for edge in edges:
            graph.add_edge(
                edge.source_node,
                edge.target_node,
                weight=edge.weight,
                edge_type=edge.edge_type,
                **edge.properties
            )

        self._nx_graph = graph
        return graph