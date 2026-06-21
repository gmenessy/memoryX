"""
Integration Tests - Event & Memory System Integration
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_event_to_memory_workflow(test_client):
    """Test complete workflow: Event → Memory → Retrieval."""
    # Step 1: Create a user input event
    event_data = {
        "event_type": "user_input",
        "actor": "user_123",
        "scope": "session_ai_learning",
        "payload": {
            "message": "What is machine learning?",
            "context": "educational"
        },
        "metadata": {
            "source": "web_interface",
            "timestamp": "2025-01-15T10:30:00Z"
        }
    }

    event_response = await test_client.post("/api/events/", json=event_data)
    assert event_response.status_code == 201
    event_id = event_response.json()["event_id"]

    # Step 2: Create semantic memory from the event
    memory_data = {
        "memory_type": "semantic",
        "title": "Machine Learning Definition",
        "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "confidence": 0.95,
        "scope": "session_ai_learning",
        "source_events": [event_id]
    }

    memory_response = await test_client.post("/api/memory/", json=memory_data)
    assert memory_response.status_code == 201
    memory_id = memory_response.json()["memory_id"]

    # Step 3: Create procedural memory (how to apply ML)
    procedural_memory = {
        "memory_type": "procedural",
        "title": "How to Apply Machine Learning",
        "content": "1. Collect data 2. Prepare data 3. Choose model 4. Train model 5. Evaluate model",
        "confidence": 0.85,
        "scope": "session_ai_learning",
        "source_events": [event_id]
    }

    procedural_response = await test_client.post("/api/memory/", json=procedural_memory)
    assert procedural_response.status_code == 201

    # Step 4: Verify memories are linked to the event
    memories_from_event = await test_client.get(f"/api/memory/event/{event_id}")
    assert memories_from_event.status_code == 200
    memories = memories_from_event.json()
    assert len(memories) == 2
    assert all(event_id in m["source_events"] for m in memories)

    # Step 5: Search for memories about machine learning
    search_results = await test_client.get("/api/memory/search?query=machine+learning")
    assert search_results.status_code == 200
    search_memories = search_results.json()
    assert len(search_memories) >= 2

    # Step 6: Get event statistics
    event_stats = await test_client.get("/api/events/statistics?scope=session_ai_learning")
    assert event_stats.status_code == 200
    stats = event_stats.json()
    assert stats["total_events"] == 1
    assert stats["by_event_type"]["user_input"] == 1

    # Step 7: Get memory statistics
    memory_stats = await test_client.get("/api/memory/statistics?scope=session_ai_learning")
    assert memory_stats.status_code == 200
    mem_stats = memory_stats.json()
    assert mem_stats["total_memories"] == 2
    assert mem_stats["by_memory_type"]["semantic"] == 1
    assert mem_stats["by_memory_type"]["procedural"] == 1


@pytest.mark.asyncio
async def test_multi_agent_workflow(test_client):
    """Test multi-agent workflow with different actors."""
    # Agent 1 makes a decision
    decision_event = {
        "event_type": "decision",
        "actor": "agent_analyzer",
        "scope": "case_456",
        "payload": {
            "decision": "analyze_user_request",
            "reasoning": "User needs information retrieval"
        }
    }

    decision_response = await test_client.post("/api/events/", json=decision_event)
    assert decision_response.status_code == 201
    decision_id = decision_response.json()["event_id"]

    # Agent 2 executes tool call
    tool_event = {
        "event_type": "tool_call",
        "actor": "agent_retriever",
        "scope": "case_456",
        "payload": {
            "tool": "vector_search",
            "query": "user request",
            "results_count": 5
        }
    }

    tool_response = await test_client.post("/api/events/", json=tool_event)
    assert tool_response.status_code == 201
    tool_id = tool_response.json()["event_id"]

    # Create memory about the successful workflow
    workflow_memory = {
        "memory_type": "procedural",
        "title": "Multi-Agent Analysis Workflow",
        "content": "1. Analyzer agent decides approach 2. Retriever agent executes search 3. Results combined",
        "confidence": 0.9,
        "scope": "case_456",
        "source_events": [decision_id, tool_id]
    }

    memory_response = await test_client.post("/api/memory/", json=workflow_memory)
    assert memory_response.status_code == 201

    # Verify both events are referenced
    memory = await test_client.get(f"/api/memory/{memory_response.json()['memory_id']}")
    assert memory.status_code == 200
    memory_data = memory.json()
    assert len(memory_data["source_events"]) == 2
    assert decision_id in memory_data["source_events"]
    assert tool_id in memory_data["source_events"]


@pytest.mark.asyncio
async def test_error_recovery_workflow(test_client):
    """Test workflow with error handling and recovery."""
    # Initial failure event
    failure_event = {
        "event_type": "failure",
        "actor": "agent_processor",
        "scope": "case_789",
        "payload": {
            "error": "database_connection_timeout",
            "retry_count": 3
        }
    }

    failure_response = await test_client.post("/api/events/", json=failure_event)
    assert failure_response.status_code == 201
    failure_id = failure_response.json()["event_id"]

    # Create risk memory
    risk_memory = {
        "memory_type": "risk",
        "title": "Database Connection Timeout Risk",
        "content": "Database connections may timeout under high load. Implement retry logic and connection pooling.",
        "confidence": 0.95,
        "scope": "case_789",
        "source_events": [failure_id]
    }

    risk_response = await test_client.post("/api/memory/", json=risk_memory)
    assert risk_response.status_code == 201

    # Subsequent success event (recovery)
    success_event = {
        "event_type": "success",
        "actor": "agent_processor",
        "scope": "case_789",
        "payload": {
            "action": "processed_with_retry",
            "attempts": 4
        }
    }

    success_response = await test_client.post("/api/events/", json=success_event)
    assert success_response.status_code == 201

    # Update risk memory with lower confidence (risk mitigated)
    update_data = {
        "confidence": 0.6  # Lower confidence after successful recovery
    }

    memory_id = risk_response.json()["memory_id"]
    update_response = await test_client.put(f"/api/memory/{memory_id}", json=update_data)
    assert update_response.status_code == 200
    assert update_response.json()["confidence"] == 0.6


@pytest.mark.asyncio
async def test_governance_workflow(test_client):
    """Test governance and policy enforcement workflow."""
    # Policy violation event
    violation_event = {
        "event_type": "policy_violation",
        "actor": "agent_automation",
        "scope": "production",
        "payload": {
            "violation": "attempted_deployment_without_approval",
            "policy": "all_deployments_require_approval"
        }
    }

    violation_response = await test_client.post("/api/events/", json=violation_event)
    assert violation_response.status_code == 201
    violation_id = violation_response.json()["event_id"]

    # Create governance memory
    governance_memory = {
        "memory_type": "governance",
        "title": "Deployment Approval Policy",
        "content": "All deployments to production require explicit approval from authorized personnel.",
        "confidence": 1.0,
        "scope": "production",
        "source_events": [violation_id]
    }

    governance_response = await test_client.post("/api/memory/", json=governance_memory)
    assert governance_response.status_code == 201

    # Create preference memory for future behavior
    preference_memory = {
        "memory_type": "preference",
        "title": "Always Request Deployment Approval",
        "content": "Before any deployment action, verify approval status",
        "confidence": 0.9,
        "scope": "agent_automation",
        "source_events": [violation_id]
    }

    preference_response = await test_client.post("/api/memory/", json=preference_memory)
    assert preference_response.status_code == 201

    # Verify governance memory exists and has high confidence
    governance_id = governance_response.json()["memory_id"]
    governance_check = await test_client.get(f"/api/memory/{governance_id}")
    assert governance_check.status_code == 200
    governance_data = governance_check.json()
    assert governance_data["confidence"] == 1.0
    assert governance_data["memory_type"] == "governance"


@pytest.mark.asyncio
async def test_skill_learning_workflow(test_client):
    """Test skill acquisition and learning workflow."""
    # Agent action demonstrating new skill
    skill_event = {
        "event_type": "agent_action",
        "actor": "agent_learner",
        "scope": "training_session_1",
        "payload": {
            "action": "successful_code_refactoring",
            "language": "python",
            "complexity": "high"
        }
    }

    skill_response = await test_client.post("/api/events/", json=skill_event)
    assert skill_response.status_code == 201
    skill_id = skill_response.json()["event_id"]

    # Create skill memory
    skill_memory = {
        "memory_type": "skill",
        "title": "Python Code Refactoring",
        "content": "Ability to refactor Python code for improved readability and performance",
        "confidence": 0.8,
        "scope": "agent_learner",
        "source_events": [skill_id]
    }

    skill_memory_response = await test_client.post("/api/memory/", json=skill_memory)
    assert skill_memory_response.status_code == 201

    # Practice the skill again (increases confidence)
    practice_event = {
        "event_type": "success",
        "actor": "agent_learner",
        "scope": "training_session_2",
        "payload": {
            "action": "another_successful_refactoring",
            "improvement": "execution_time_decreased"
        }
    }

    practice_response = await test_client.post("/api/events/", json=practice_event)
    assert practice_response.status_code == 201

    # Update skill memory with higher confidence
    skill_id = skill_memory_response.json()["memory_id"]
    confidence_update = {
        "confidence": 0.95
    }

    update_response = await test_client.put(f"/api/memory/{skill_id}", json=confidence_update)
    assert update_response.status_code == 200
    assert update_response.json()["confidence"] == 0.95


@pytest.mark.asyncio
async def test_episodic_memory_formation(test_client):
    """Test episodic memory formation from sequence of events."""
    events = [
        {
            "event_type": "user_input",
            "actor": "user_alice",
            "scope": "conversation_123",
            "payload": {"message": "I need help with debugging"}
        },
        {
            "event_type": "agent_action",
            "actor": "agent_debugger",
            "scope": "conversation_123",
            "payload": {"action": "started_debugging_session"}
        },
        {
            "event_type": "tool_call",
            "actor": "agent_debugger",
            "scope": "conversation_123",
            "payload": {"tool": "code_analyzer", "result": "found_bug"}
        },
        {
            "event_type": "success",
            "actor": "agent_debugger",
            "scope": "conversation_123",
            "payload": {"outcome": "bug_fixed", "time_taken": "5_minutes"}
        }
    ]

    created_events = []
    for event in events:
        response = await test_client.post("/api/events/", json=event)
        assert response.status_code == 201
        created_events.append(response.json())

    # Create episodic memory from the sequence
    episodic_memory = {
        "memory_type": "episodic",
        "title": "Debugging Session with User Alice",
        "content": "User Alice requested debugging help. Agent started session, used code analyzer, found and fixed bug within 5 minutes.",
        "confidence": 0.9,
        "scope": "conversation_123",
        "source_events": [e["event_id"] for e in created_events]
    }

    episodic_response = await test_client.post("/api/memory/", json=episodic_memory)
    assert episodic_response.status_code == 201

    # Verify episodic memory references all events
    episodic_id = episodic_response.json()["memory_id"]
    episodic_check = await test_client.get(f"/api/memory/{episodic_id}")
    assert episodic_check.status_code == 200
    episodic_data = episodic_check.json()
    assert len(episodic_data["source_events"]) == 4

    # Verify memory can be retrieved from any of the source events
    for event in created_events:
        event_memories = await test_client.get(f"/api/memory/event/{event['event_id']}")
        assert event_memories.status_code == 200
        memories = event_memories.json()
        assert any(m["memory_id"] == episodic_id for m in memories)