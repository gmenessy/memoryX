"""
Dream Engine Tests
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.dream import (
    DaydreamJobCreate,
    NightdreamJobCreate,
    DeepdreamJobCreate,
    TransformationType,
    DreamType,
    DreamStatus,
)


# Daydream Tests


@pytest.mark.asyncio
async def test_create_daydream_job(test_client):
    """Test creating a daydream job."""
    # First create an event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "user_input",
        "actor": "user_123",
        "scope": "test",
        "payload": {"message": "Test message"}
    })
    event_id = event_response.json()["event_id"]

    job_data = {
        "source_events": [event_id],
        "transformation_type": "direct",
        "processing_params": {
            "memory_type": "episodic",
            "title": "Test Memory"
        },
        "priority": 0.8
    }

    response = await test_client.post("/api/dream/daydream/jobs", json=job_data)

    assert response.status_code == 201
    data = response.json()
    assert data["dream_type"] == "daydream"
    assert data["status"] == "pending"
    assert data["transformation_type"] == "direct"
    assert len(data["source_events"]) == 1
    assert data["priority"] == 0.8


@pytest.mark.asyncio
async def test_create_daydream_job_invalid_event(test_client):
    """Test creating daydream job with invalid event fails."""
    job_data = {
        "source_events": [uuid4()],
        "transformation_type": "direct"
    }

    response = await test_client.post("/api/dream/daydream/jobs", json=job_data)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_daydream_job(test_client):
    """Test getting a daydream job by ID."""
    # Create event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "decision",
        "actor": "agent_1",
        "scope": "test",
        "payload": {"decision": "test decision"}
    })
    event_id = event_response.json()["event_id"]

    # Create job
    job_response = await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "inferred"
    })
    job_id = job_response.json()["job_id"]

    # Get job
    response = await test_client.get(f"/api/dream/daydream/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["transformation_type"] == "inferred"


@pytest.mark.asyncio
async def test_list_daydream_jobs(test_client):
    """Test listing daydream jobs."""
    # Create event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "test",
        "actor": "user",
        "scope": "test",
        "payload": {}
    })
    event_id = event_response.json()["event_id"]

    # Create multiple jobs
    for i in range(3):
        await test_client.post("/api/dream/daydream/jobs", json={
            "source_events": [event_id],
            "transformation_type": "direct",
            "priority": 0.5 + i * 0.1
        })

    response = await test_client.get("/api/dream/daydream/jobs")

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 3


@pytest.mark.asyncio
async def test_list_daydream_jobs_with_filters(test_client):
    """Test listing daydream jobs with filters."""
    # Create event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "test",
        "actor": "user",
        "scope": "test",
        "payload": {}
    })
    event_id = event_response.json()["event_id"]

    # Create jobs with different transformation types
    await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "direct"
    })

    await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "aggregated"
    })

    # Filter by transformation type
    response = await test_client.get("/api/dream/daydream/jobs?transformation_type=direct")
    assert response.status_code == 200
    jobs = response.json()
    assert all(j["transformation_type"] == "direct" for j in jobs)


@pytest.mark.asyncio
async def test_process_daydream_job_direct(test_client):
    """Test processing a daydream job with direct transformation."""
    # Create event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "user_input",
        "actor": "user_123",
        "scope": "test_scope",
        "payload": {
            "description": "Test event for memory transformation"
        }
    })
    event_id = event_response.json()["event_id"]

    # Create job
    job_response = await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "direct",
        "processing_params": {
            "memory_type": "episodic",
            "title": "Test Memory from Event"
        }
    })
    job_id = job_response.json()["job_id"]

    # Process job
    process_response = await test_client.post(f"/api/dream/daydream/jobs/{job_id}/process")
    assert process_response.status_code == 200

    # Wait a bit for background processing
    import asyncio
    await asyncio.sleep(0.5)

    # Check job status
    job_status = await test_client.get(f"/api/dream/daydream/jobs/{job_id}")
    job_data = job_status.json()

    # Job should be completed or running
    assert job_data["status"] in ["completed", "running"]

    # If completed, check result
    if job_data["status"] == "completed":
        assert job_data["target_memory"] is not None
        assert job_data["result"] is not None


@pytest.mark.asyncio
async def test_process_daydream_job_aggregated(test_client):
    """Test processing daydream job with aggregated transformation."""
    # Create multiple events
    event_ids = []
    for i in range(3):
        event_response = await test_client.post("/api/events/", json={
            "event_type": "log_entry",
            "actor": "system",
            "scope": "logs",
            "payload": {
                "title": f"Log Entry {i}",
                "content": f"Log content {i}"
            }
        })
        event_ids.append(event_response.json()["event_id"])

    # Create aggregated job
    job_response = await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": event_ids,
        "transformation_type": "aggregated",
        "processing_params": {
            "memory_type": "semantic",
            "title": "Aggregated Log Entries"
        }
    })
    job_id = job_response.json()["job_id"]

    # Process job
    await test_client.post(f"/api/dream/daydream/jobs/{job_id}/process")

    # Check job was accepted
    job_status = await test_client.get(f"/api/dream/daydream/jobs/{job_id}")
    assert job_status.status_code == 200


@pytest.mark.asyncio
async def test_count_daydream_jobs(test_client):
    """Test counting daydream jobs."""
    response = await test_client.get("/api/dream/daydream/jobs/count")
    assert response.status_code == 200
    assert "count" in response.json()


@pytest.mark.asyncio
async def test_get_pending_daydream_jobs(test_client):
    """Test getting pending daydream jobs."""
    # Create event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "test",
        "actor": "user",
        "scope": "test",
        "payload": {}
    })
    event_id = event_response.json()["event_id"]

    # Create pending job
    await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "direct",
        "priority": 0.9
    })

    response = await test_client.get("/api/dream/daydream/jobs/pending")

    assert response.status_code == 200
    jobs = response.json()
    # Should contain at least our job
    assert len(jobs) >= 1


@pytest.mark.asyncio
async def test_delete_daydream_job(test_client):
    """Test deleting a daydream job."""
    # Create event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "test",
        "actor": "user",
        "scope": "test",
        "payload": {}
    })
    event_id = event_response.json()["event_id"]

    # Create job
    job_response = await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "direct"
    })
    job_id = job_response.json()["job_id"]

    # Delete job
    response = await test_client.delete(f"/api/dream/daydream/jobs/{job_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = await test_client.get(f"/api/dream/daydream/jobs/{job_id}")
    assert get_response.status_code == 404


# Nightdream Tests


@pytest.mark.asyncio
async def test_create_nightdream_job(test_client):
    """Test creating a nightdream job."""
    job_data = {
        "operation": "merge",
        "scope": "test_scope",
        "target_memories": [],
        "processing_params": {}
    }

    response = await test_client.post("/api/dream/nightdream/jobs", json=job_data)

    assert response.status_code == 201
    data = response.json()
    assert data["dream_type"] == "nightdream"
    assert data["operation"] == "merge"
    assert data["scope"] == "test_scope"


@pytest.mark.asyncio
async def test_create_nightdream_job_invalid_operation(test_client):
    """Test creating nightdream job with invalid operation fails."""
    job_data = {
        "operation": "invalid_operation",
        "scope": "test",
        "target_memories": []
    }

    response = await test_client.post("/api/dream/nightdream/jobs", json=job_data)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_nightdream_job(test_client):
    """Test getting a nightdream job by ID."""
    job_data = {
        "operation": "compress",
        "scope": "production",
        "target_memories": []
    }

    create_response = await test_client.post("/api/dream/nightdream/jobs", json=job_data)
    job_id = create_response.json()["job_id"]

    response = await test_client.get(f"/api/dream/nightdream/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["operation"] == "compress"


@pytest.mark.asyncio
async def test_list_nightdream_jobs(test_client):
    """Test listing nightdream jobs."""
    # Create multiple jobs
    for op in ["merge", "compress", "deduplicate"]:
        await test_client.post("/api/dream/nightdream/jobs", json={
            "operation": op,
            "scope": "test",
            "target_memories": []
        })

    response = await test_client.get("/api/dream/nightdream/jobs")

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 3


@pytest.mark.asyncio
async def test_list_nightdream_jobs_with_filters(test_client):
    """Test listing nightdream jobs with operation filter."""
    # Create jobs
    await test_client.post("/api/dream/nightdream/jobs", json={
        "operation": "merge",
        "scope": "test",
        "target_memories": []
    })

    await test_client.post("/api/dream/nightdream/jobs", json={
        "operation": "compress",
        "scope": "test",
        "target_memories": []
    })

    # Filter by operation
    response = await test_client.get("/api/dream/nightdream/jobs?operation=merge")
    assert response.status_code == 200
    jobs = response.json()
    assert all(j["operation"] == "merge" for j in jobs)


@pytest.mark.asyncio
async def test_scheduled_nightdream_job(test_client):
    """Test creating a scheduled nightdream job."""
    scheduled_time = datetime.utcnow() + timedelta(hours=1)

    job_data = {
        "operation": "deduplicate",
        "scope": "global",
        "target_memories": [],
        "scheduled_for": scheduled_time.isoformat()
    }

    response = await test_client.post("/api/dream/nightdream/jobs", json=job_data)

    assert response.status_code == 201
    data = response.json()
    assert data["scheduled_for"] is not None


@pytest.mark.asyncio
async def test_count_nightdream_jobs(test_client):
    """Test counting nightdream jobs."""
    response = await test_client.get("/api/dream/nightdream/jobs/count")
    assert response.status_code == 200
    assert "count" in response.json()


@pytest.mark.asyncio
async def test_get_scheduled_nightdream_jobs(test_client):
    """Test getting scheduled nightdream jobs."""
    # Create a job without schedule (due immediately)
    await test_client.post("/api/dream/nightdream/jobs", json={
        "operation": "merge",
        "scope": "test",
        "target_memories": []
    })

    response = await test_client.get("/api/dream/nightdream/jobs/scheduled")

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 1


@pytest.mark.asyncio
async def test_delete_nightdream_job(test_client):
    """Test deleting a nightdream job."""
    create_response = await test_client.post("/api/dream/nightdream/jobs", json={
        "operation": "merge",
        "scope": "test",
        "target_memories": []
    })
    job_id = create_response.json()["job_id"]

    response = await test_client.delete(f"/api/dream/nightdream/jobs/{job_id}")
    assert response.status_code == 204


# Deepdream Tests


@pytest.mark.asyncio
async def test_create_deepdream_job(test_client):
    """Test creating a deepdream job."""
    job_data = {
        "operation": "pattern_discovery",
        "scope": "global",
        "analysis_depth": "standard",
        "processing_params": {}
    }

    response = await test_client.post("/api/dream/deepdream/jobs", json=job_data)

    assert response.status_code == 201
    data = response.json()
    assert data["dream_type"] == "deepdream"
    assert data["operation"] == "pattern_discovery"
    assert data["analysis_depth"] == "standard"


@pytest.mark.asyncio
async def test_create_deepdream_job_invalid_operation(test_client):
    """Test creating deepdream job with invalid operation fails."""
    job_data = {
        "operation": "invalid_operation",
        "scope": "test",
        "analysis_depth": "standard"
    }

    response = await test_client.post("/api/dream/deepdream/jobs", json=job_data)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_deepdream_job(test_client):
    """Test getting a deepdream job by ID."""
    job_data = {
        "operation": "policy_discovery",
        "scope": "production",
        "analysis_depth": "deep"
    }

    create_response = await test_client.post("/api/dream/deepdream/jobs", json=job_data)
    job_id = create_response.json()["job_id"]

    response = await test_client.get(f"/api/dream/deepdream/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["operation"] == "policy_discovery"


@pytest.mark.asyncio
async def test_list_deepdream_jobs(test_client):
    """Test listing deepdream jobs."""
    # Create multiple jobs
    for op in ["pattern_discovery", "policy_discovery", "dna_evolution"]:
        await test_client.post("/api/dream/deepdream/jobs", json={
            "operation": op,
            "scope": "global",
            "analysis_depth": "standard"
        })

    response = await test_client.get("/api/dream/deepdream/jobs")

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 3


@pytest.mark.asyncio
async def test_list_deepdream_jobs_with_filters(test_client):
    """Test listing deepdream jobs with operation filter."""
    # Create jobs
    await test_client.post("/api/dream/deepdream/jobs", json={
        "operation": "pattern_discovery",
        "scope": "test",
        "analysis_depth": "quick"
    })

    await test_client.post("/api/dream/deepdream/jobs", json={
        "operation": "policy_discovery",
        "scope": "test",
        "analysis_depth": "standard"
    })

    # Filter by operation
    response = await test_client.get("/api/dream/deepdream/jobs?operation=pattern_discovery")
    assert response.status_code == 200
    jobs = response.json()
    assert all(j["operation"] == "pattern_discovery" for j in jobs)


@pytest.mark.asyncio
async def test_count_deepdream_jobs(test_client):
    """Test counting deepdream jobs."""
    response = await test_client.get("/api/dream/deepdream/jobs/count")
    assert response.status_code == 200
    assert "count" in response.json()


@pytest.mark.asyncio
async def test_delete_deepdream_job(test_client):
    """Test deleting a deepdream job."""
    create_response = await test_client.post("/api/dream/deepdream/jobs", json={
        "operation": "pattern_discovery",
        "scope": "test",
        "analysis_depth": "quick"
    })
    job_id = create_response.json()["job_id"]

    response = await test_client.delete(f"/api/dream/deepdream/jobs/{job_id}")
    assert response.status_code == 204


# Statistics Tests


@pytest.mark.asyncio
async def test_get_dream_statistics(test_client):
    """Test getting dream engine statistics."""
    # Create some jobs to ensure statistics
    event_response = await test_client.post("/api/events/", json={
        "event_type": "test",
        "actor": "user",
        "scope": "test",
        "payload": {}
    })
    event_id = event_response.json()["event_id"]

    await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "direct"
    })

    await test_client.post("/api/dream/nightdream/jobs", json={
        "operation": "merge",
        "scope": "test",
        "target_memories": []
    })

    await test_client.post("/api/dream/deepdream/jobs", json={
        "operation": "pattern_discovery",
        "scope": "test",
        "analysis_depth": "quick"
    })

    response = await test_client.get("/api/dream/statistics")

    assert response.status_code == 200
    stats = response.json()

    assert "daydream" in stats
    assert "nightdream" in stats
    assert "deepdream" in stats

    # Check structure
    for dream_type in ["daydream", "nightdream", "deepdream"]:
        assert "total" in stats[dream_type]
        assert "pending" in stats[dream_type]
        assert "running" in stats[dream_type]
        assert "completed" in stats[dream_type]
        assert "failed" in stats[dream_type]


# Metadata Tests


@pytest.mark.asyncio
async def test_get_dream_types(test_client):
    """Test getting available dream types."""
    response = await test_client.get("/api/dream/types")

    assert response.status_code == 200
    types = response.json()

    assert "dream_types" in types
    assert "statuses" in types
    assert "transformation_types" in types
    assert "nightdream_operations" in types
    assert "deepdream_operations" in types
    assert "analysis_depths" in types

    # Check values
    assert "daydream" in types["dream_types"]
    assert "nightdream" in types["dream_types"]
    assert "deepdream" in types["dream_types"]
    assert "direct" in types["transformation_types"]
    assert "merge" in types["nightdream_operations"]
    assert "pattern_discovery" in types["deepdream_operations"]


# Integration Tests


@pytest.mark.asyncio
async def test_complete_daydream_workflow(test_client):
    """Test complete daydream workflow: event → job → process → memory."""
    # 1. Create event
    event_response = await test_client.post("/api/events/", json={
        "event_type": "user_input",
        "actor": "user_123",
        "scope": "workflow_test",
        "payload": {
            "title": "Important Decision",
            "description": "We decided to implement feature X",
            "reasoning": "It will improve user experience"
        }
    })
    event_id = event_response.json()["event_id"]

    # 2. Create daydream job
    job_response = await test_client.post("/api/dream/daydream/jobs", json={
        "source_events": [event_id],
        "transformation_type": "inferred",
        "processing_params": {
            "memory_type": "decision",
            "title": "Decision: Implement Feature X"
        },
        "priority": 0.9
    })
    job_id = job_response.json()["job_id"]

    # 3. Process job
    process_response = await test_client.post(f"/api/dream/daydream/jobs/{job_id}/process")
    assert process_response.status_code == 200

    # 4. Check job created memory
    import asyncio
    await asyncio.sleep(1)  # Wait for processing

    job_status = await test_client.get(f"/api/dream/daydream/jobs/{job_id}")
    job_data = job_status.json()

    # Should have created a memory
    if job_data["status"] == "completed":
        assert job_data["target_memory"] is not None

        # 5. Verify memory exists
        memory_response = await test_client.get(f"/api/memory/{job_data['target_memory']}")
        assert memory_response.status_code == 200
        memory_data = memory_response.json()
        assert memory_data["memory_type"] == "decision"
        assert event_id in memory_data["source_events"]


@pytest.mark.asyncio
async def test_multiple_daydream_transformation_types(test_client):
    """Test all daydream transformation types."""
    # Create events for each transformation type

    # For direct
    event1 = await test_client.post("/api/events/", json={
        "event_type": "simple_event",
        "actor": "user",
        "scope": "test",
        "payload": {"content": "Simple content"}
    }})

    # For aggregated (need multiple events)
    event_ids = []
    for i in range(3):
        e = await test_client.post("/api/events/", json={
            "event_type": "log",
            "actor": "system",
            "scope": "test",
            "payload": {"entry": f"Log {i}"}
        })
        event_ids.append(e.json()["event_id"])

    # For extracted
    event3 = await test_client.post("/api/events/", json={
        "event_type": "complex_event",
        "actor": "user",
        "scope": "test",
        "payload": {
            "title": "Complex Event",
            "content": "Main content here",
            "metadata": {"extra": "data"}
        }
    }})

    # For inferred
    event4 = await test_client.post("/api/events/", json={
        "event_type": "decision_event",
        "actor": "agent",
        "scope": "test",
        "payload": {
            "decision": "Choose option A",
            "reasoning": "Better performance"
        }
    }})

    # Create jobs for each transformation type
    transformations = [
        ("direct", [event1.json()["event_id"]]),
        ("aggregated", event_ids),
        ("extracted", [event3.json()["event_id"]]),
        ("inferred", [event4.json()["event_id"]])
    ]

    for trans_type, src_events in transformations:
        job = await test_client.post("/api/dream/daydream/jobs", json={
            "source_events": src_events,
            "transformation_type": trans_type,
            "processing_params": {"memory_type": "episodic"}
        })
        assert job.status_code == 201
        assert job.json()["transformation_type"] == trans_type
