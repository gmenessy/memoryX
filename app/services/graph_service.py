"""
Graph Service - Business Logic Layer for Memory Graph
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.repositories.graph_repository import GraphRepository


class GraphService:
    """
    Service layer for Memory Graph operations.
    Handles business logic and validation for graph operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.graph_repo = GraphRepository(session)

    async def create_node(self, node_data: GraphNodeCreate) -> GraphNodeResponse:
        """
        Create a new graph node with validation.

        Args:
            node_data: Node creation data

        Returns:
            Created node response

        Raises:
            ValueError: If validation fails
        """
        # Validate node type
        if node_data.node_type.value not in NODE_TYPES:
            raise ValueError(
                f"Invalid node type: {node_data.node_type}. "
                f"Must be one of: {', '.join(NODE_TYPES)}"
            )

        # Check if node with external_id already exists
        existing = await self.graph_repo.get_node_by_external_id(node_data.external_id)
        if existing:
            raise ValueError(f"Node with external_id {node_data.external_id} already exists")

        # Validate label
        if not node_data.label.strip():
            raise ValueError("Label cannot be empty")

        return await self.graph_repo.create_node(node_data)

    async def get_node(self, node_id: UUID) -> GraphNodeResponse | None:
        """Get node by ID."""
        return await self.graph_repo.get_node(node_id)

    async def get_node_by_external_id(self, external_id: UUID) -> GraphNodeResponse | None:
        """Get node by external ID."""
        return await self.graph_repo.get_node_by_external_id(external_id)

    async def list_nodes(
        self,
        node_type: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphNodeResponse]:
        """List nodes with filtering."""
        # Validate limit
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")

        if limit < 1:
            raise ValueError("Limit must be at least 1")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

        return await self.graph_repo.list_nodes(node_type, limit, offset)

    async def create_edge(self, edge_data: GraphEdgeCreate) -> GraphEdgeResponse:
        """
        Create a new graph edge with validation.

        Args:
            edge_data: Edge creation data

        Returns:
            Created edge response

        Raises:
            ValueError: If validation fails
        """
        # Validate edge type
        if edge_data.edge_type.value not in EDGE_TYPES:
            raise ValueError(
                f"Invalid edge type: {edge_data.edge_type}. "
                f"Must be one of: {', '.join(EDGE_TYPES)}"
            )

        # Validate nodes are different
        if edge_data.source_node == edge_data.target_node:
            raise ValueError("Source and target nodes must be different")

        return await self.graph_repo.create_edge(edge_data)

    async def get_edge(self, edge_id: UUID) -> GraphEdgeResponse | None:
        """Get edge by ID."""
        return await self.graph_repo.get_edge(edge_id)

    async def list_edges(
        self,
        source_node: UUID | None = None,
        target_node: UUID | None = None,
        edge_type: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GraphEdgeResponse]:
        """List edges with filtering."""
        return await self.graph_repo.list_edges(source_node, target_node, edge_type, limit, offset)

    async def get_neighbors(self, node_id: UUID) -> list[GraphNodeResponse]:
        """
        Get neighboring nodes.

        Args:
            node_id: Node ID

        Returns:
            List of neighboring nodes
        """
        # Validate node exists
        node = await self.graph_repo.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        return await self.graph_repo.get_neighbors(node_id)

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
        # Validate nodes exist
        source = await self.graph_repo.get_node(source_id)
        target = await self.graph_repo.get_node(target_id)

        if not source:
            raise ValueError(f"Source node {source_id} not found")
        if not target:
            raise ValueError(f"Target node {target_id} not found")

        if source_id == target_id:
            raise ValueError("Source and target nodes must be different")

        return await self.graph_repo.find_shortest_path(source_id, target_id, max_depth)

    async def find_related_nodes(
        self,
        node_id: UUID,
        max_distance: int = 2,
        max_results: int = 50
    ) -> list[GraphNodeResponse]:
        """
        Find nodes related to a given node within specified distance.

        Args:
            node_id: Starting node ID
            max_distance: Maximum distance in graph
            max_results: Maximum number of results

        Returns:
            List of related nodes
        """
        # Validate node exists
        node = await self.graph_repo.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        graph = await self.graph_repo._get_networkx_graph()

        try:
            # Find all nodes within max_distance
            related_ids = []
            lengths = nx.single_source_shortest_path_length(graph, node_id, cutoff=max_distance)

            # Exclude the starting node
            for related_id, distance in lengths.items():
                if related_id != node_id:
                    related_ids.append((related_id, distance))

            # Sort by distance and limit results
            related_ids.sort(key=lambda x: x[1])
            related_ids = related_ids[:max_results]

            # Get node objects
            nodes = []
            for related_id, _ in related_ids:
                node_obj = await self.graph_repo.get_node(related_id)
                if node_obj:
                    nodes.append(node_obj)

            return nodes

        except nx.NetworkXError:
            return []

    async def get_graph_statistics(self) -> GraphStatistics:
        """
        Get graph statistics.

        Returns:
            Graph statistics
        """
        return await self.graph_repo.get_graph_statistics()

    async def auto_create_memory_node(self, memory_id: UUID, memory_type: str, title: str) -> GraphNodeResponse:
        """
        Automatically create a graph node from a memory card.

        Args:
            memory_id: Memory card ID
            memory_type: Memory type
            title: Memory title

        Returns:
            Created node response
        """
        node_data = GraphNodeCreate(
            node_type="memory",
            external_id=memory_id,
            label=title[:500],  # Truncate if too long
            properties={"memory_type": memory_type}
        )

        return await self.create_node(node_data)

    async def auto_create_event_node(self, event_id: UUID, event_type: str, actor: str) -> GraphNodeResponse:
        """
        Automatically create a graph node from an event.

        Args:
            event_id: Event ID
            event_type: Event type
            actor: Event actor

        Returns:
            Created node response
        """
        node_data = GraphNodeCreate(
            node_type="event",
            external_id=event_id,
            label=f"{event_type} by {actor}"[:500],
            properties={"event_type": event_type, "actor": actor}
        )

        return await self.create_node(node_data)

    async def create_memory_source_edge(self, memory_id: UUID, event_id: UUID) -> GraphEdgeResponse:
        """
        Automatically create an edge from memory to its source event.

        Args:
            memory_id: Memory ID
            event_id: Source event ID

        Returns:
            Created edge response
        """
        # Get or create nodes
        memory_node = await self.graph_repo.get_node_by_external_id(memory_id)
        event_node = await self.graph_repo.get_node_by_external_id(event_id)

        if not memory_node:
            # This should not happen if nodes are auto-created
            raise ValueError(f"Memory node {memory_id} not found")

        if not event_node:
            # This should not happen if nodes are auto-created
            raise ValueError(f"Event node {event_id} not found")

        edge_data = GraphEdgeCreate(
            source_node=memory_node.node_id,
            target_node=event_node.node_id,
            edge_type="derived_from",
            weight=0.8,
            properties={"auto_created": True}
        )

        return await self.create_edge(edge_data)