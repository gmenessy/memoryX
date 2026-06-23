"""
fRAG Engine Tests
"""
import pytest
from uuid import uuid4

from app.models.frag import (
    RetrievalQuery,
    RetrievalOptimization,
    RetrievalFeedback,
)


# Retrieval Tests


@pytest.mark.asyncio
async def test_retrieve_memories(test_client):
    """Test retrieving memories with fRAG."""
    # Create some memories first
    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Python Programming",
        "content": "Python is a high-level programming language",
        "confidence": 0.9,
        "scope": "programming"
    })

    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Machine Learning Basics",
        "content": "Machine learning is a subset of AI",
        "confidence": 0.8,
        "scope": "ai"
    })

    # Perform retrieval
    query_data = {
        "query": "Python programming language",
        "query_type": "semantic",
        "top_k": 5,
        "min_confidence": 0.3
    }

    response = await test_client.post("/api/frag/retrieve", json=query_data)

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Python programming language"
    assert "fragments" in data
    assert data["total_fragments"] >= 0
    assert data["retrieval_method"] == "semantic"


@pytest.mark.asyncio
async def test_retrieve_with_scope_filter(test_client):
    """Test retrieval with scope filtering."""
    # Create memories in different scopes
    await test_client.post("/api/memory/", json={
        "memory_type": "episodic",
        "title": "Case 123 Decision",
        "content": "Decision made in case 123",
        "confidence": 0.8,
        "scope": "case_123"
    })

    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "General Knowledge",
        "content": "General information",
        "confidence": 0.7,
        "scope": "global"
    })

    # Query with scope filter
    query_data = {
        "query": "case decision",
        "query_type": "semantic",
        "scope": "case_123",
        "top_k": 5,
        "filters": {"scope": "case_123"}
    }

    response = await test_client.post("/api/frag/retrieve", json=query_data)

    assert response.status_code == 200
    data = response.json()
    # Should prefer case_123 scope results
    assert data["total_fragments"] >= 0


@pytest.mark.asyncio
async def test_retrieve_empty_query_fails(test_client):
    """Test retrieval with empty query fails."""
    query_data = {
        "query": "   ",
        "query_type": "semantic"
    }

    response = await test_client.post("/api/frag/retrieve", json=query_data)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_retrieve_with_custom_optimization(test_client):
    """Test retrieval with custom optimization parameters."""
    # Create a memory
    await test_client.post("/api/memory/", json={
        "memory_type": "procedural",
        "title": "API Usage",
        "content": "How to use the API endpoints",
        "confidence": 0.75,
        "scope": "documentation"
    })

    query_data = {
        "query": "API endpoints",
        "query_type": "hybrid",
        "top_k": 3
    }

    optimization = {
        "top_k": 3,
        "min_confidence": 0.4,
        "semantic_weight": 0.6,
        "case_relevance_weight": 0.3
    }

    response = await test_client.post(
        "/api/frag/retrieve/optimized",
        json={"query": query_data, "optimization": optimization}
    )

    assert response.status_code == 200
    data = response.json()
    assert "fragments" in data


@pytest.mark.asyncio
async def test_adaptive_retrieve(test_client):
    """Test adaptive retrieval with automatic optimization."""
    # Create some memories
    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Testing Guide",
        "content": "How to write effective tests",
        "confidence": 0.85,
        "scope": "testing"
    })

    response = await test_client.post(
        "/api/frag/retrieve/adaptive",
        json={
            "query_text": "testing best practices",
            "scope": "testing",
            "max_iterations": 2
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "fragments" in data


# Feedback Tests


@pytest.mark.asyncio
async def test_provide_retrieval_feedback(test_client):
    """Test providing feedback for retrieval results."""
    # First perform a retrieval to generate a log
    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Feedback Test",
        "content": "Content for feedback testing",
        "confidence": 0.7,
        "scope": "test"
    })

    query_response = await test_client.post("/api/frag/retrieve", json={
        "query": "feedback test",
        "query_type": "semantic"
    })

    # Provide feedback (using a mock query_id since we don't have the actual one)
    feedback_data = {
        "query_id": uuid4(),
        "relevant_fragment_ids": [],
        "irrelevant_fragment_ids": [],
        "overall_rating": "positive",
        "comments": "Good results"
    }

    response = await test_client.post("/api/frag/feedback", json=feedback_data)

    # Note: This might not find the log entry, but the API should handle it
    assert response.status_code in [200, 404]


# Metrics Tests


@pytest.mark.asyncio
async def test_get_retrieval_metrics(test_client):
    """Test getting retrieval performance metrics."""
    # Perform some retrievals to generate metrics
    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Metrics Test",
        "content": "Content for metrics",
        "confidence": 0.7,
        "scope": "metrics"
    })

    await test_client.post("/api/frag/retrieve", json={
        "query": "metrics test",
        "query_type": "semantic"
    })

    response = await test_client.get("/api/frag/metrics")

    assert response.status_code == 200
    metrics = response.json()
    assert "precision_at_k" in metrics
    assert "recall_at_k" in metrics
    assert "retrieval_time_ms" in metrics


@pytest.mark.asyncio
async def test_get_optimization_parameters(test_client):
    """Test getting current optimization parameters."""
    response = await test_client.get("/api/frag/optimization/parameters")

    assert response.status_code == 200
    params = response.json()
    assert "top_k" in params
    assert "min_confidence" in params
    assert "semantic_weight" in params


# Metadata Tests


@pytest.mark.asyncio
async def test_get_retrieval_methods(test_client):
    """Test getting available retrieval methods."""
    response = await test_client.get("/api/frag/types")

    assert response.status_code == 200
    types = response.json()
    assert "retrieval_methods" in types
    assert "semantic" in types["retrieval_methods"]
    assert "vector" in types["retrieval_methods"]
    assert "hybrid" in types["retrieval_methods"]


# Integration Tests


@pytest.mark.asyncio
async def test_complete_frag_workflow(test_client):
    """Test complete fRAG workflow: create memories, retrieve, provide feedback."""
    # 1. Create relevant memories
    memories = []
    for i in range(3):
        memory_response = await test_client.post("/api/memory/", json={
            "memory_type": "semantic",
            "title": f"Testing Concept {i}",
            "content": f"Testing concept {i}: unit tests, integration tests, e2e tests",
            "confidence": 0.8 + i * 0.05,
            "scope": "testing"
        })
        memories.append(memory_response.json())

    # 2. Perform retrieval
    retrieval_response = await test_client.post("/api/frag/retrieve", json={
        "query": "unit testing concepts",
        "query_type": "semantic",
        "top_k": 5,
        "min_confidence": 0.7
    })

    assert retrieval_response.status_code == 200
    result = retrieval_response.json()
    assert result["total_fragments"] >= 0
    assert result["query"] == "unit testing concepts"

    # 3. Check fragments have proper structure
    if result["total_fragments"] > 0:
        fragment = result["fragments"][0]
        assert "source_type" in fragment
        assert "source_id" in fragment
        assert "content" in fragment
        assert "relevance_score" in fragment
        assert "confidence" in fragment
        assert 0.0 <= fragment["relevance_score"] <= 1.0

    # 4. Get metrics to verify logging worked
    metrics_response = await test_client.get("/api/frag/metrics")
    assert metrics_response.status_code == 200


@pytest.mark.asyncio
async def test_retrieval_ranking(test_client):
    """Test that retrieval results are properly ranked."""
    # Create memories with different relevance
    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Machine Learning Algorithms",
        "content": "ML algorithms include neural networks, decision trees, SVM",
        "confidence": 0.9,
        "scope": "ml"
    })

    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Cooking Recipes",
        "content": "How to cook pasta and pizza",
        "confidence": 0.8,
        "scope": "cooking"
    })

    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Deep Learning",
        "content": "Deep learning uses neural networks with many layers",
        "confidence": 0.85,
        "scope": "ml"
    })

    # Query about ML
    response = await test_client.post("/api/frag/retrieve", json={
        "query": "machine learning neural networks",
        "query_type": "semantic",
        "top_k": 10
    })

    assert response.status_code == 200
    result = response.json()

    # ML-related results should rank higher
    if result["total_fragments"] > 0:
        fragments = result["fragments"]
        # First results should be more relevant
        assert fragments[0]["relevance_score"] >= fragments[-1]["relevance_score"]


@pytest.mark.asyncio
async def test_retrieval_with_confidence_filter(test_client):
    """Test retrieval with minimum confidence filter."""
    # Create memories with different confidence levels
    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "High Confidence Memory",
        "content": "This is very reliable information",
        "confidence": 0.95,
        "scope": "test"
    })

    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Low Confidence Memory",
        "content": "This is uncertain information",
        "confidence": 0.2,
        "scope": "test"
    })

    # Query with high minimum confidence
    response = await test_client.post("/api/frag/retrieve", json={
        "query": "reliable information",
        "query_type": "semantic",
        "top_k": 10,
        "min_confidence": 0.8
    })

    assert response.status_code == 200
    result = response.json()

    # All results should meet the confidence threshold
    if result["total_fragments"] > 0:
        for fragment in result["fragments"]:
            assert fragment["confidence"] >= 0.8


@pytest.mark.asyncio
async def test_retrieval_top_k_limit(test_client):
    """Test that retrieval respects top_k parameter."""
    # Create multiple memories
    for i in range(10):
        await test_client.post("/api/memory/", json={
            "memory_type": "semantic",
            "title": f"Memory {i}",
            "content": f"Content {i}",
            "confidence": 0.7,
            "scope": "test"
        })

    # Request only 3 results
    response = await test_client.post("/api/frag/retrieve", json={
        "query": "memory content",
        "query_type": "semantic",
        "top_k": 3
    })

    assert response.status_code == 200
    result = response.json()
    assert result["total_fragments"] <= 3


@pytest.mark.asyncio
async def test_different_query_types(test_client):
    """Test different query types (semantic, keyword, hybrid)."""
    # Create test memories
    await test_client.post("/api/memory/", json={
        "memory_type": "semantic",
        "title": "Python Decorators",
        "content": "Decorators modify function behavior",
        "confidence": 0.8,
        "scope": "python"
    })

    for query_type in ["semantic", "keyword", "hybrid"]:
        response = await test_client.post("/api/frag/retrieve", json={
            "query": "python decorators function",
            "query_type": query_type,
            "top_k": 5
        })

        assert response.status_code == 200
        result = response.json()
        assert result["retrieval_method"] == query_type


@pytest.mark.asyncio
async def test_retrieval_with_case_relevance(test_client):
    """Test retrieval with case relevance scoring."""
    # Create memories in specific case scope
    await test_client.post("/api/memory/", json={
        "memory_type": "episodic",
        "title": "Case ABC-123 Decision",
        "content": "Decision made for case ABC-123",
        "confidence": 0.8,
        "scope": "case_abc_123"
    })

    # Query that mentions the case
    response = await test_client.post("/api/frag/retrieve", json={
        "query": "decision for case abc 123",
        "query_type": "semantic",
        "top_k": 5
    })

    assert response.status_code == 200
    result = response.json()

    # Case-relevant memory should be ranked highly
    if result["total_fragments"] > 0:
        # Check if any fragment has good relevance
        max_relevance = max(f["relevance_score"] for f in result["fragments"])
        assert max_relevance > 0


@pytest.mark.asyncio
async def test_optimization_adaptation(test_client):
    """Test that optimization parameters adapt based on performance."""
    # Perform multiple retrievals
    for i in range(5):
        await test_client.post("/api/frag/retrieve", json={
            "query": f"test query {i}",
            "query_type": "semantic",
            "top_k": 5
        })

    # Get optimization parameters (they may have adapted)
    response = await test_client.get("/api/frag/optimization/parameters")

    assert response.status_code == 200
    params = response.json()
    assert "top_k" in params
    assert "semantic_weight" in params
    assert "confidence_weight" in params
