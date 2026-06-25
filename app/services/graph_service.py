"""
Graph Service - Business Logic Layer for Memory Graph
"""
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
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

logger = get_logger(__name__)


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

    # Advanced Graph Algorithms

    async def get_node_centrality(
        self,
        node_id: UUID,
        centrality_type: str = "degree"
    ) -> float:
        """
        Calculate centrality measure for a node.

        Args:
            node_id: Node ID
            centrality_type: Type of centrality (degree, betweenness, eigenvector, pagerank)

        Returns:
            Centrality score

        Raises:
            ValueError: If node not found or centrality type invalid
        """
        # Validate node exists
        node = await self.graph_repo.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        graph = await self.graph_repo._get_networkx_graph()

        if node_id not in graph:
            return 0.0

        try:
            if centrality_type == "degree":
                # Degree centrality
                return graph.degree(node_id) / (len(graph) - 1) if len(graph) > 1 else 0.0

            elif centrality_type == "betweenness":
                # Betweenness centrality
                centrality = nx.betweenness_centrality(graph)
                return centrality.get(node_id, 0.0)

            elif centrality_type == "eigenvector":
                # Eigenvector centrality
                centrality = nx.eigenvector_centrality(graph, max_iter=1000)
                return centrality.get(node_id, 0.0)

            elif centrality_type == "pagerank":
                # PageRank
                centrality = nx.pagerank(graph)
                return centrality.get(node_id, 0.0)

            else:
                raise ValueError(f"Invalid centrality type: {centrality_type}")

        except nx.NetworkXError:
            logger.warning(f"NetworkX error calculating centrality for node {node_id}")
            return 0.0

    async def get_community_clusters(
        self,
        cluster_method: str = "louvain",
        min_cluster_size: int = 3
    ) -> dict[str, list[UUID]]:
        """
        Detect communities/clusters in the graph.

        Args:
            cluster_method: Method for clustering (louvain, label_propagation, greedy)
            min_cluster_size: Minimum size for a cluster to be returned

        Returns:
            Dictionary mapping cluster IDs to lists of node IDs
        """
        graph = await self.graph_repo._get_networkx_graph()

        if len(graph.nodes()) == 0:
            return {}

        try:
            if cluster_method == "louvain":
                # Louvain community detection
                import networkx.algorithms.community as nx_community
                communities = nx_community.louvain_communities(graph)

            elif cluster_method == "label_propagation":
                # Label propagation
                import networkx.algorithms.community as nx_community
                communities = nx_community.label_propagation_communities(graph)

            elif cluster_method == "greedy":
                # Greedy modularity maximization
                import networkx.algorithms.community as nx_community
                communities = nx_community.greedy_modularity_communities(graph)

            else:
                raise ValueError(f"Invalid cluster method: {cluster_method}")

            # Convert to dict and filter by size
            clusters = {}
            for i, community in enumerate(communities):
                if len(community) >= min_cluster_size:
                    clusters[f"cluster_{i}"] = list(community)

            logger.info(f"Found {len(clusters)} clusters using {cluster_method}")
            return clusters

        except Exception as e:
            logger.error(f"Error in community detection: {e}")
            return {}

    async def extract_subgraph(
        self,
        seed_node_ids: list[UUID],
        max_depth: int = 2,
        max_nodes: int = 100
    ) -> dict[str, Any]:
        """
        Extract a subgraph around seed nodes.

        Args:
            seed_node_ids: List of starting node IDs
            max_depth: Maximum distance from seed nodes
            max_nodes: Maximum number of nodes to include

        Returns:
            Dictionary with nodes, edges, and metadata
        """
        if not seed_node_ids:
            return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

        graph = await self.graph_repo._get_networkx_graph()

        try:
            # Start with seed nodes
            subgraph_nodes = set(seed_node_ids)

            # BFS to collect nodes within max_depth
            current_depth_nodes = set(seed_node_ids)
            for depth in range(max_depth):
                if len(subgraph_nodes) >= max_nodes:
                    break

                next_depth_nodes = set()
                for node_id in current_depth_nodes:
                    if node_id in graph:
                        neighbors = list(graph.neighbors(node_id))
                        for neighbor in neighbors:
                            if neighbor not in subgraph_nodes:
                                subgraph_nodes.add(neighbor)
                                next_depth_nodes.add(neighbor)

                                if len(subgraph_nodes) >= max_nodes:
                                    break

                current_depth_nodes = next_depth_nodes
                if not current_depth_nodes:
                    break

            # Get edges between selected nodes
            subgraph_edges = []
            for node_id in subgraph_nodes:
                if node_id in graph:
                    for neighbor in graph.neighbors(node_id):
                        if neighbor in subgraph_nodes:
                            edge_data = graph.get_edge_data(node_id, neighbor)
                            if edge_data:
                                subgraph_edges.append({
                                    "source": node_id,
                                    "target": neighbor,
                                    "weight": edge_data.get("weight", 1.0)
                                })

            # Get node details
            node_details = []
            for node_id in list(subgraph_nodes)[:max_nodes]:
                node = await self.graph_repo.get_node(node_id)
                if node:
                    node_details.append({
                        "node_id": str(node.node_id),
                        "label": node.label,
                        "node_type": node.node_type,
                        "external_id": str(node.external_id)
                    })

            return {
                "nodes": node_details,
                "edges": subgraph_edges[:max_nodes * 2],  # Limit edges
                "node_count": len(node_details),
                "edge_count": len(subgraph_edges),
                "max_depth_reached": max_depth,
                "truncated": len(subgraph_nodes) > max_nodes
            }

        except Exception as e:
            logger.error(f"Error extracting subgraph: {e}")
            return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

    async def find_paths_ranked(
        self,
        source_id: UUID,
        target_id: UUID,
        max_paths: int = 10,
        max_length: int = 5
    ) -> list[dict[str, Any]]:
        """
        Find multiple paths between nodes, ranked by weight/quality.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_paths: Maximum number of paths to return
            max_length: Maximum path length

        Returns:
            List of paths with metadata, ranked by quality
        """
        # Validate nodes exist
        source = await self.graph_repo.get_node(source_id)
        target = await self.graph_repo.get_node(target_id)

        if not source or not target:
            raise ValueError("Source or target node not found")

        graph = await self.graph_repo._get_networkx_graph()

        try:
            # Find all simple paths up to max_length
            paths = list(nx.all_simple_paths(
                graph,
                source_id,
                target_id,
                cutoff=max_length
            ))

            if not paths:
                return []

            # Calculate quality score for each path
            ranked_paths = []
            for path in paths[:max_paths * 2]:  # Get more than needed for ranking
                path_quality = 0.0
                path_weight = 0.0

                # Calculate path metrics
                for i in range(len(path) - 1):
                    edge_data = graph.get_edge_data(path[i], path[i + 1])
                    if edge_data:
                        weight = edge_data.get("weight", 1.0)
                        path_weight += weight

                # Average weight (higher is better)
                path_quality = path_weight / (len(path) - 1) if len(path) > 1 else 0.0

                # Shorter paths get bonus
                path_quality += (max_length - len(path) + 1) * 0.1

                ranked_paths.append({
                    "path": [str(node_id) for node_id in path],
                    "length": len(path),
                    "weight": path_weight,
                    "quality_score": path_quality
                })

            # Sort by quality score (descending)
            ranked_paths.sort(key=lambda x: x["quality_score"], reverse=True)

            return ranked_paths[:max_paths]

        except nx.NetworkXError:
            logger.warning(f"NetworkX error finding paths between {source_id} and {target_id}")
            return []

    async def bidirectional_search(
        self,
        source_id: UUID,
        target_id: UUID,
        max_depth: int = 5
    ) -> GraphTraversalResult | None:
        """
        Bidirectional BFS search for shortest path.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_depth: Maximum search depth from each side

        Returns:
            Path result or None if no path found
        """
        graph = await self.graph_repo._get_networkx_graph()

        try:
            if source_id not in graph or target_id not in graph:
                return None

            # Bidirectional BFS
            from collections import deque

            forward_queue = deque([(source_id, [source_id])])
            backward_queue = deque([(target_id, [target_id])])

            forward_visited = {source_id: [source_id]}
            backward_visited = {target_id: [target_id]}

            meeting_node = None
            meeting_path = None

            for depth in range(max_depth):
                # Forward search
                if forward_queue:
                    current, path = forward_queue.popleft()

                    if current == target_id:
                        meeting_node = current
                        meeting_path = path
                        break

                    for neighbor in graph.neighbors(current):
                        if neighbor not in forward_visited:
                            forward_visited[neighbor] = path + [neighbor]
                            forward_queue.append((neighbor, path + [neighbor]))

                            # Check if we've met
                            if neighbor in backward_visited:
                                meeting_node = neighbor
                                # Combine paths
                                meeting_path = path + backward_visited[neighbor][::-1]
                                break

                if meeting_node:
                    break

                # Backward search
                if backward_queue:
                    current, path = backward_queue.popleft()

                    for neighbor in graph.neighbors(current):
                        if neighbor not in backward_visited:
                            backward_visited[neighbor] = path + [neighbor]
                            backward_queue.append((neighbor, path + [neighbor]))

                            # Check if we've met
                            if neighbor in forward_visited:
                                meeting_node = neighbor
                                # Combine paths (reverse backward path)
                                meeting_path = forward_visited[neighbor] + path[::-1]
                                break

                if meeting_node:
                    break

            if meeting_path:
                # Get node and edge details
                nodes = []
                edges = []

                for node_id in meeting_path:
                    node = await self.graph_repo.get_node(node_id)
                    if node:
                        nodes.append(node)

                for i in range(len(meeting_path) - 1):
                    edge = await self.graph_repo.get_edge_by_nodes(
                        meeting_path[i],
                        meeting_path[i + 1]
                    )
                    if edge:
                        edges.append(edge)

                total_weight = sum(e.weight for e in edges) if edges else 0.0

                return GraphTraversalResult(
                    path=[n.node_id for n in nodes],
                    nodes=nodes,
                    edges=edges,
                    total_weight=total_weight,
                    length=len(meeting_path) - 1
                )

            return None

        except Exception as e:
            logger.error(f"Error in bidirectional search: {e}")
            return None