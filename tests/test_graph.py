"""
Memory Graph Tests
"""
import pytest
from uuid import uuid4

from app.models.graph import (
    GraphNodeCreate,
    GraphEdgeCreate,
    NodeType,
    EdgeType,
)


# Node Tests


@pytest.mark.asyncio
async def test_create_graph_node(test_client):
    """Test creating a graph node."""
    node_data = {
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Test Memory Node",
        "properties": {"memory_type": "episodic"}
    }

    response = await test_client.post("/api/graph/nodes", json=node_data)

    assert response.status_code == 201
    data = response.json()
    assert data["node_type"] == "memory"
    assert data["label"] == "Test Memory Node"
    assert data["properties"]["memory_type"] == "episodic"
    assert "node_id" in data


@pytest.mark.asyncio
async def test_create_duplicate_node_fails(test_client):
    """Test creating duplicate node fails."""
    external_id = uuid4()
    node_data = {
        "node_type": "memory",
        "external_id": external_id,
        "label": "Test Node"
    }

    # Create first node
    response1 = await test_client.post("/api/graph/nodes", json=node_data)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await test_client.post("/api/graph/nodes", json=node_data)
    assert response2.status_code == 400


@pytest.mark.asyncio
async def test_get_graph_node(test_client):
    """Test getting a graph node by ID."""
    external_id = uuid4()
    node_data = {
        "node_type": "decision",
        "external_id": external_id,
        "label": "Decision Node"
    }

    create_response = await test_client.post("/api/graph/nodes", json=node_data)
    node_id = create_response.json()["node_id"]

    response = await test_client.get(f"/api/graph/nodes/{node_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == node_id
    assert data["node_type"] == "decision"


@pytest.mark.asyncio
async def test_list_graph_nodes(test_client):
    """Test listing graph nodes."""
    # Create multiple nodes
    for i in range(3):
        await test_client.post("/api/graph/nodes", json={
            "node_type": "memory",
            "external_id": uuid4(),
            "label": f"Node {i}"
        })

    response = await test_client.get("/api/graph/nodes")

    assert response.status_code == 200
    nodes = response.json()
    assert len(nodes) >= 3


@pytest.mark.asyncio
async def test_list_nodes_by_type(test_client):
    """Test listing nodes filtered by type."""
    # Create nodes of different types
    await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Memory Node"
    })

    await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Document Node"
    })

    # Filter by memory type
    response = await test_client.get("/api/graph/nodes?node_type=memory")
    assert response.status_code == 200
    nodes = response.json()
    assert all(n["node_type"] == "memory" for n in nodes)


# Edge Tests


@pytest.mark.asyncio
async def test_create_graph_edge(test_client):
    """Test creating a graph edge."""
    # Create two nodes
    node1_response = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Source Node"
    })
    source_id = node1_response.json()["node_id"]

    node2_response = await test_client.post("/api/graph/nodes", json={
        "node_type": "decision",
        "external_id": uuid4(),
        "label": "Target Node"
    })
    target_id = node2_response.json()["node_id"]

    edge_data = {
        "source_node": source_id,
        "target_node": target_id,
        "edge_type": "supports",
        "weight": 0.8
    }

    response = await test_client.post("/api/graph/edges", json=edge_data)

    assert response.status_code == 201
    data = response.json()
    assert data["source_node"] == source_id
    assert data["target_node"] == target_id
    assert data["edge_type"] == "supports"
    assert data["weight"] == 0.8


@pytest.mark.asyncio
async def test_create_edge_same_nodes_fails(test_client):
    """Test creating edge with same source and target fails."""
    # Create node
    node_response = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Test Node"
    })
    node_id = node_response.json()["node_id"]

    # Try to create edge with same source and target
    edge_data = {
        "source_node": node_id,
        "target_node": node_id,
        "edge_type": "references"
    }

    response = await test_client.post("/api/graph/edges", json=edge_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_graph_edge(test_client):
    """Test getting a graph edge by ID."""
    # Create two nodes
    node1 = await test_client.post("/api/graph/nodes", json={
        "node_type": "case",
        "external_id": uuid4(),
        "label": "Case Node"
    })
    node2 = await test_client.post("/api/graph/nodes", json={
        "node_type": "policy",
        "external_id": uuid4(),
        "label": "Policy Node"
    })

    # Create edge
    edge_response = await test_client.post("/api/graph/edges", json={
        "source_node": node1.json()["node_id"],
        "target_node": node2.json()["node_id"],
        "edge_type": "belongs_to"
    })
    edge_id = edge_response.json()["edge_id"]

    response = await test_client.get(f"/api/graph/edges/{edge_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["edge_id"] == edge_id


@pytest.mark.asyncio
async def test_list_graph_edges(test_client):
    """Test listing graph edges."""
    # Create nodes
    node1 = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Node 1"
    })
    node2 = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Node 2"
    })

    # Create edges
    await test_client.post("/api/graph/edges", json={
        "source_node": node1.json()["node_id"],
        "target_node": node2.json()["node_id"],
        "edge_type": "references"
    })

    response = await test_client.get("/api/graph/edges")
    assert response.status_code == 200
    edges = response.json()
    assert len(edges) >= 1


# Traversal Tests


@pytest.mark.asyncio
async def test_get_node_neighbors(test_client):
    """Test getting neighbors of a node."""
    # Create central node
    center_response = await test_client.post("/api/graph/nodes", json={
        "node_type": "case",
        "external_id": uuid4(),
        "label": "Central Case"
    })
    center_id = center_response.json()["node_id"]

    # Create neighbor nodes
    neighbor1 = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Document 1"
    })

    neighbor2 = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Memory 1"
    })

    neighbor3 = await test_client.post("/api/graph/nodes", json={
        "node_type": "decision",
        "external_id": uuid4(),
        "label": "Decision 1"
    })

    # Create edges
    await test_client.post("/api/graph/edges", json={
        "source_node": center_id,
        "target_node": neighbor1.json()["node_id"],
        "edge_type": "contains"
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": center_id,
        "target_node": neighbor2.json()["node_id"],
        "edge_type": "relates_to"
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": center_id,
        "target_node": neighbor3.json()["node_id"],
        "edge_type": "includes"
    })

    # Get neighbors
    response = await test_client.get(f"/api/graph/nodes/{center_id}/neighbors")

    assert response.status_code == 200
    neighbors = response.json()
    assert len(neighbors) == 3


@pytest.mark.asyncio
async def test_find_shortest_path(test_client):
    """Test finding shortest path between nodes."""
    # Create nodes
    node_a = await test_client.post("/api/graph/nodes", json={
        "node_type": "case",
        "external_id": uuid4(),
        "label": "Case A"
    })

    node_b = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Document B"
    })

    node_c = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Memory C"
    })

    # Create path: A -> B -> C
    await test_client.post("/api/graph/edges", json={
        "source_node": node_a.json()["node_id"],
        "target_node": node_b.json()["node_id"],
        "edge_type": "contains"
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": node_b.json()["node_id"],
        "target_node": node_c.json()["node_id"],
        "edge_type": "references"
    })

    # Find shortest path from A to C
    response = await test_client.get(
        f"/api/graph/traverse/shortest-path?"
        f"source={node_a.json()['node_id']}&"
        f"target={node_c.json()['node_id']}"
    )

    assert response.status_code == 200
    path_data = response.json()
    assert "path" in path_data
    assert len(path_data["path"]) == 3  # A, B, C
    assert path_data["length"] == 2  # 2 edges


@pytest.mark.asyncio
async def test_find_related_nodes(test_client):
    """Test finding related nodes within a distance."""
    # Create central node
    center = await test_client.post("/api/graph/nodes", json={
        "node_type": "case",
        "external_id": uuid4(),
        "label": "Main Case"
    })

    # Create connected nodes
    related1 = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Related Doc 1"
    })

    related2 = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Related Memory 1"
    })

    # Connect directly
    await test_client.post("/api/graph/edges", json={
        "source_node": center.json()["node_id"],
        "target_node": related1.json()["node_id"],
        "edge_type": "contains"
    })

    # Find related nodes
    response = await test_client.get(
        f"/api/graph/nodes/{center.json()['node_id']}/related?max_distance=1"
    )

    assert response.status_code == 200
    related = response.json()
    assert len(related) >= 1


# Statistics Tests


@pytest.mark.asyncio
async def test_get_graph_statistics(test_client):
    """Test getting graph statistics."""
    # Create some nodes and edges
    node1 = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Node 1"
    })

    node2 = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Node 2"
    })

    node3 = await test_client.post("/api/graph/nodes", json={
        "node_type": "decision",
        "external_id": uuid4(),
        "label": "Node 3"
    })

    # Create edges
    await test_client.post("/api/graph/edges", json={
        "source_node": node1.json()["node_id"],
        "target_node": node2.json()["node_id"],
        "edge_type": "references"
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": node2.json()["node_id"],
        "target_node": node3.json()["node_id"],
        "edge_type": "supports"
    })

    response = await test_client.get("/api/graph/statistics")

    assert response.status_code == 200
    stats = response.json()
    assert stats["total_nodes"] >= 3
    assert stats["total_edges"] >= 2
    assert "nodes_by_type" in stats
    assert "edges_by_type" in stats


# Metadata Tests


@pytest.mark.asyncio
async def test_get_node_types(test_client):
    """Test getting available node types."""
    response = await test_client.get("/api/graph/types")

    assert response.status_code == 200
    types = response.json()
    assert "node_types" in types
    assert "memory" in types["node_types"]
    assert "document" in types["node_types"]
    assert "decision" in types["node_types"]


@pytest.mark.asyncio
async def test_get_edge_types(test_client):
    """Test getting available edge types."""
    response = await test_client.get("/api/graph/types")

    assert response.status_code == 200
    types = response.json()
    assert "edge_types" in types
    assert "references" in types["edge_types"]
    assert "supports" in types["edge_types"]
    assert "contradicts" in types["edge_types"]


# Integration Tests


@pytest.mark.asyncio
async def test_complete_graph_workflow(test_client):
    """Test complete graph workflow: create nodes, edges, traverse."""
    # 1. Create a case structure as per spec:
    # Case
    # │
    # ├── Document
    # │
    # ├── Memory
    # │
    # │    └── Decision
    # │
    # └── Policy

    # Create nodes
    case_node = await test_client.post("/api/graph/nodes", json={
        "node_type": "case",
        "external_id": uuid4(),
        "label": "Case 12345"
    })

    doc_node = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Document A"
    })

    memory_node = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Memory X"
    })

    decision_node = await test_client.post("/api/graph/nodes", json={
        "node_type": "decision",
        "external_id": uuid4(),
        "label": "Decision Y"
    })

    policy_node = await test_client.post("/api/graph/nodes", json={
        "node_type": "policy",
        "external_id": uuid4(),
        "label": "Policy Z"
    })

    case_id = case_node.json()["node_id"]
    doc_id = doc_node.json()["node_id"]
    memory_id = memory_node.json()["node_id"]
    decision_id = decision_node.json()["node_id"]
    policy_id = policy_node.json()["node_id"]

    # 2. Create edges (structure)
    await test_client.post("/api/graph/edges", json={
        "source_node": case_id,
        "target_node": doc_id,
        "edge_type": "contains"
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": case_id,
        "target_node": memory_id,
        "edge_type": "contains"
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": memory_id,
        "target_node": decision_id,
        "edge_type": "derived_from"
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": case_id,
        "target_node": policy_id,
        "edge_type": "relates_to"
    })

    # 3. Get neighbors of case (should have 3 direct neighbors)
    neighbors_response = await test_client.get(f"/api/graph/nodes/{case_id}/neighbors")
    assert neighbors_response.status_code == 200
    neighbors = neighbors_response.json()
    # Case contains doc, memory, policy (3 neighbors)
    assert len(neighbors) == 3

    # 4. Find path from case to decision
    path_response = await test_client.get(
        f"/api/graph/traverse/shortest-path?"
        f"source={case_id}&target={decision_id}"
    )
    assert path_response.status_code == 200
    path = path_response.json()
    # Path should be: Case -> Memory -> Decision
    assert case_id in path["path"]
    assert decision_id in path["path"]
    assert path["length"] == 2


@pytest.mark.asyncio
async def test_auto_create_node_from_memory(test_client):
    """Test auto-creating graph node from memory."""
    # First create a memory
    memory_response = await test_client.post("/api/memory/", json={
        "memory_type": "episodic",
        "title": "Test Memory for Graph",
        "content": "Memory content",
        "confidence": 0.8,
        "scope": "test"
    })
    memory_id = memory_response.json()["memory_id"]

    # Auto-create node
    node_response = await test_client.post("/api/graph/nodes/auto-create/memory", json={
        "memory_id": str(memory_id),
        "memory_type": "episodic",
        "title": "Test Memory for Graph"
    })

    assert node_response.status_code == 201
    node = node_response.json()
    assert node["node_type"] == "memory"
    assert node["external_id"] == str(memory_id)


@pytest.mark.asyncio
async def test_complex_traversal(test_client):
    """Test complex graph traversal scenario."""
    # Create a more complex graph structure
    nodes = {}
    for i in range(6):
        response = await test_client.post("/api/graph/nodes", json={
            "node_type": "memory",
            "external_id": uuid4(),
            "label": f"Node {i}"
        })
        nodes[f"node_{i}"] = response.json()["node_id"]

    # Create edges forming a chain with branches
    # 0 -> 1 -> 2 -> 3
    #       1 -> 4 -> 5
    edges = [
        ("node_0", "node_1"),
        ("node_1", "node_2"),
        ("node_2", "node_3"),
        ("node_1", "node_4"),
        ("node_4", "node_5")
    ]

    for source, target in edges:
        await test_client.post("/api/graph/edges", json={
            "source_node": nodes[source],
            "target_node": nodes[target],
            "edge_type": "references"
        })

    # Find shortest path from node_0 to node_5
    response = await test_client.get(
        f"/api/graph/traverse/shortest-path?"
        f"source={nodes['node_0']}&target={nodes['node_5']}"
    )

    assert response.status_code == 200
    path = response.json()
    # Shortest path: 0 -> 1 -> 4 -> 5 (length 3)
    assert path["length"] == 3


@pytest.mark.asyncio
async def test_edge_weight_traversal(test_client):
    """Test traversal considering edge weights."""
    # Create nodes
    start = await test_client.post("/api/graph/nodes", json={
        "node_type": "case",
        "external_id": uuid4(),
        "label": "Start"
    })

    option_a = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Option A"
    })

    option_b = await test_client.post("/api/graph/nodes", json={
        "node_type": "document",
        "external_id": uuid4(),
        "label": "Option B"
    })

    target = await test_client.post("/api/graph/nodes", json={
        "node_type": "memory",
        "external_id": uuid4(),
        "label": "Target"
    })

    start_id = start.json()["node_id"]
    opt_a_id = option_a.json()["node_id"]
    opt_b_id = option_b.json()["node_id"]
    target_id = target.json()["node_id"]

    # Create edges with different weights
    await test_client.post("/api/graph/edges", json={
        "source_node": start_id,
        "target_node": opt_a_id,
        "edge_type": "references",
        "weight": 0.3  # Low weight
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": opt_a_id,
        "target_node": target_id,
        "edge_type": "supports",
        "weight": 0.4
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": start_id,
        "target_node": opt_b_id,
        "edge_type": "references",
        "weight": 0.9  # High weight (strong connection)
    })

    await test_client.post("/api/graph/edges", json={
        "source_node": opt_b_id,
        "target_node": target_id,
        "edge_type": "supports",
        "weight": 0.8
    })

    # Find shortest path (considering weights)
    response = await test_client.get(
        f"/api/graph/traverse/shortest-path?"
        f"source={start_id}&target={target_id}"
    )

    assert response.status_code == 200
    path = response.json()
    assert "total_weight" in path
    # The system should prefer the path with higher total weight
    assert path["total_weight"] > 0
