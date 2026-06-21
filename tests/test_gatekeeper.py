"""
Gatekeeper Tests - Memory Gatekeeper System
"""
import pytest
from uuid import uuid4

from app.models.gatekeeper import (
    PolicyCreate,
    PolicyUpdate,
    RiskAssessmentCreate,
    GatekeeperCheckCreate,
    GatekeeperAction,
    RiskLevel,
)


# Policy Tests


@pytest.mark.asyncio
async def test_create_policy(test_client):
    """Test creating a new policy."""
    policy_data = {
        "name": "test_no_deploy_without_snapshot",
        "description": "Kein Deploy ohne Snapshot",
        "condition": {"action": "deploy", "has_snapshot": False},
        "action": "block",
        "severity": "high",
        "scope": "production",
        "active": True
    }

    response = await test_client.post("/api/gatekeeper/policies", json=policy_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == policy_data["name"]
    assert data["action"] == "block"
    assert data["severity"] == "high"
    assert data["active"] is True
    assert "policy_id" in data


@pytest.mark.asyncio
async def test_create_duplicate_policy(test_client):
    """Test creating duplicate policy fails."""
    policy_data = {
        "name": "duplicate_test",
        "description": "Test policy",
        "condition": {"action": "test"},
        "action": "warn",
        "severity": "low",
        "scope": "test"
    }

    # Create first policy
    response1 = await test_client.post("/api/gatekeeper/policies", json=policy_data)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await test_client.post("/api/gatekeeper/policies", json=policy_data)
    assert response2.status_code == 400


@pytest.mark.asyncio
async def test_get_policy(test_client):
    """Test getting a policy by ID."""
    # Create policy first
    policy_data = {
        "name": "get_test_policy",
        "description": "Test get policy",
        "condition": {"action": "delete"},
        "action": "review",
        "severity": "medium",
        "scope": "global"
    }
    create_response = await test_client.post("/api/gatekeeper/policies", json=policy_data)
    policy_id = create_response.json()["policy_id"]

    # Get policy
    response = await test_client.get(f"/api/gatekeeper/policies/{policy_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["policy_id"] == policy_id
    assert data["name"] == "get_test_policy"


@pytest.mark.asyncio
async def test_list_policies(test_client):
    """Test listing policies."""
    # Create multiple policies
    for i in range(3):
        policy_data = {
            "name": f"list_test_policy_{i}",
            "description": f"Test policy {i}",
            "condition": {"action": f"action_{i}"},
            "action": "warn",
            "severity": "low",
            "scope": "test"
        }
        await test_client.post("/api/gatekeeper/policies", json=policy_data)

    # List policies
    response = await test_client.get("/api/gatekeeper/policies?scope=test")

    assert response.status_code == 200
    policies = response.json()
    assert len(policies) >= 3


@pytest.mark.asyncio
async def test_update_policy(test_client):
    """Test updating a policy."""
    # Create policy
    policy_data = {
        "name": "update_test_policy",
        "description": "Original description",
        "condition": {"action": "test"},
        "action": "warn",
        "severity": "low",
        "scope": "test"
    }
    create_response = await test_client.post("/api/gatekeeper/policies", json=policy_data)
    policy_id = create_response.json()["policy_id"]

    # Update policy
    update_data = {
        "description": "Updated description",
        "severity": "high"
    }
    response = await test_client.put(f"/api/gatekeeper/policies/{policy_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["severity"] == "high"


@pytest.mark.asyncio
async def test_activate_deactivate_policy(test_client):
    """Test activating and deactivating a policy."""
    # Create policy
    policy_data = {
        "name": "activate_test_policy",
        "description": "Test activate/deactivate",
        "condition": {"action": "test"},
        "action": "warn",
        "severity": "low",
        "scope": "test",
        "active": True
    }
    create_response = await test_client.post("/api/gatekeeper/policies", json=policy_data)
    policy_id = create_response.json()["policy_id"]

    # Deactivate
    deactivate_response = await test_client.post(f"/api/gatekeeper/policies/{policy_id}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["active"] is False

    # Activate
    activate_response = await test_client.post(f"/api/gatekeeper/policies/{policy_id}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["active"] is True


@pytest.mark.asyncio
async def test_delete_policy(test_client):
    """Test deleting a policy."""
    # Create policy
    policy_data = {
        "name": "delete_test_policy",
        "description": "Test delete",
        "condition": {"action": "test"},
        "action": "warn",
        "severity": "low",
        "scope": "test"
    }
    create_response = await test_client.post("/api/gatekeeper/policies", json=policy_data)
    policy_id = create_response.json()["policy_id"]

    # Delete policy
    response = await test_client.delete(f"/api/gatekeeper/policies/{policy_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = await test_client.get(f"/api/gatekeeper/policies/{policy_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_count_policies(test_client):
    """Test counting policies."""
    response = await test_client.get("/api/gatekeeper/policies/count")
    assert response.status_code == 200
    assert "count" in response.json()


# Risk Assessment Tests


@pytest.mark.asyncio
async def test_create_risk_assessment(test_client):
    """Test creating a risk assessment."""
    risk_data = {
        "action_type": "deploy",
        "risk_level": "high",
        "risk_factors": {
            "data_loss": "medium",
            "downtime": "high",
            "rollback_difficulty": "medium"
        },
        "mitigation": "Always create backup before deploy",
        "scope": "production"
    }

    response = await test_client.post("/api/gatekeeper/risks", json=risk_data)

    assert response.status_code == 201
    data = response.json()
    assert data["action_type"] == "deploy"
    assert data["risk_level"] == "high"
    assert "assessment_id" in data


@pytest.mark.asyncio
async def test_get_risk_assessment(test_client):
    """Test getting a risk assessment by ID."""
    risk_data = {
        "action_type": "delete",
        "risk_level": "severe",
        "risk_factors": {"permanent_data_loss": "high"},
        "mitigation": "Archive instead of delete",
        "scope": "production"
    }
    create_response = await test_client.post("/api/gatekeeper/risks", json=risk_data)
    assessment_id = create_response.json()["assessment_id"]

    response = await test_client.get(f"/api/gatekeeper/risks/{assessment_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["assessment_id"] == assessment_id
    assert data["action_type"] == "delete"


@pytest.mark.asyncio
async def test_list_risk_assessments(test_client):
    """Test listing risk assessments."""
    # Create multiple risk assessments
    for i in range(3):
        risk_data = {
            "action_type": f"action_{i}",
            "risk_level": "medium",
            "risk_factors": {},
            "scope": "test"
        }
        await test_client.post("/api/gatekeeper/risks", json=risk_data)

    response = await test_client.get("/api/gatekeeper/risks?scope=test")

    assert response.status_code == 200
    risks = response.json()
    assert len(risks) >= 3


@pytest.mark.asyncio
async def test_delete_risk_assessment(test_client):
    """Test deleting a risk assessment."""
    risk_data = {
        "action_type": "test_delete",
        "risk_level": "low",
        "risk_factors": {},
        "scope": "test"
    }
    create_response = await test_client.post("/api/gatekeeper/risks", json=risk_data)
    assessment_id = create_response.json()["assessment_id"]

    response = await test_client.delete(f"/api/gatekeeper/risks/{assessment_id}")
    assert response.status_code == 204


# CORE: Gatekeeper Check Tests


@pytest.mark.asyncio
async def test_check_action_allowed(test_client):
    """Test checking an action that is allowed."""
    check_data = {
        "action": "read",
        "scope": "global",
        "actor": "user_123",
        "context": {}
    }

    response = await test_client.post("/api/gatekeeper/check", json=check_data)

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True
    assert data["action"] in ["allow", "warn"]
    assert "check_id" in data
    assert "confidence" in data


@pytest.mark.asyncio
async def test_check_action_blocked(test_client):
    """Test checking an action that is blocked by policy."""
    # Create blocking policy
    policy_data = {
        "name": "block_deploy_no_snapshot",
        "description": "Block deploy without snapshot",
        "condition": {"action": "deploy", "has_snapshot": False},
        "action": "block",
        "severity": "high",
        "scope": "production",
        "active": True
    }
    await test_client.post("/api/gatekeeper/policies", json=policy_data)

    # Check action without snapshot
    check_data = {
        "action": "deploy",
        "scope": "production",
        "actor": "user_123",
        "context": {"has_snapshot": False}
    }

    response = await test_client.post("/api/gatekeeper/check", json=check_data)

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert data["action"] == "block"
    assert len(data["blocked_policies"]) > 0


@pytest.mark.asyncio
async def test_check_action_with_warning(test_client):
    """Test checking an action that produces a warning."""
    # Create warning policy
    policy_data = {
        "name": "warn_known_failure",
        "description": "Warn about known failures",
        "condition": {"action": "retry", "known_failure": True},
        "action": "warn",
        "severity": "medium",
        "scope": "global",
        "active": True
    }
    await test_client.post("/api/gatekeeper/policies", json=policy_data)

    check_data = {
        "action": "retry",
        "scope": "global",
        "actor": "system",
        "context": {"known_failure": True}
    }

    response = await test_client.post("/api/gatekeeper/check", json=check_data)

    assert response.status_code == 200
    data = response.json()
    assert data["action"] in ["warn", "review"]
    assert len(data["warnings"]) > 0 or data["allowed"] is True


@pytest.mark.asyncio
async def test_check_history(test_client):
    """Test getting check history."""
    # Perform a check
    check_data = {
        "action": "test",
        "scope": "global",
        "actor": "user_123"
    }
    check_response = await test_client.post("/api/gatekeeper/check", json=check_data)
    check_id = check_response.json()["check_id"]

    # Get check by ID
    response = await test_client.get(f"/api/gatekeeper/checks/{check_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["check_id"] == check_id


@pytest.mark.asyncio
async def test_list_checks(test_client):
    """Test listing checks."""
    # Perform multiple checks
    for i in range(3):
        check_data = {
            "action": f"test_action_{i}",
            "scope": "test",
            "actor": "user_123"
        }
        await test_client.post("/api/gatekeeper/check", json=check_data)

    # List checks
    response = await test_client.get("/api/gatekeeper/checks?scope=test")
    assert response.status_code == 200
    checks = response.json()
    assert len(checks) >= 3


@pytest.mark.asyncio
async def test_get_statistics(test_client):
    """Test getting gatekeeper statistics."""
    # Perform some checks
    for _ in range(5):
        check_data = {
            "action": "stats_test",
            "scope": "stats_scope",
            "actor": "user_123"
        }
        await test_client.post("/api/gatekeeper/check", json=check_data)

    response = await test_client.get("/api/gatekeeper/statistics?scope=stats_scope")

    assert response.status_code == 200
    stats = response.json()
    assert "total" in stats
    assert "allowed" in stats
    assert "blocked" in stats
    assert "warnings" in stats
    assert stats["total"] >= 5


@pytest.mark.asyncio
async def test_get_types(test_client):
    """Test getting available types."""
    response = await test_client.get("/api/gatekeeper/types")

    assert response.status_code == 200
    types = response.json()
    assert "actions" in types
    assert "severities" in types
    assert "risk_levels" in types
    assert "allow" in types["actions"]
    assert "block" in types["actions"]
    assert "high" in types["severities"]
    assert "critical" in types["severities"]


@pytest.mark.asyncio
async def test_actor_history(test_client):
    """Test getting actor check history."""
    actor = "test_actor_123"

    # Perform checks for actor
    for i in range(3):
        check_data = {
            "action": f"actor_test_{i}",
            "scope": "global",
            "actor": actor
        }
        await test_client.post("/api/gatekeeper/check", json=check_data)

    # Get actor history
    response = await test_client.get(f"/api/gatekeeper/checks/actor/{actor}")
    assert response.status_code == 200
    checks = response.json()
    assert len(checks) >= 3
    # All checks should be for this actor
    for check in checks:
        assert check["actor"] == actor


@pytest.mark.asyncio
async def test_blocked_actions(test_client):
    """Test getting blocked actions."""
    scope = "blocked_test_scope"

    # Create blocking policy
    policy_data = {
        "name": "block_test_policy",
        "description": "Block test actions",
        "condition": {"action": "blocked_action"},
        "action": "block",
        "severity": "critical",
        "scope": scope,
        "active": True
    }
    await test_client.post("/api/gatekeeper/policies", json=policy_data)

    # Perform blocked check
    check_data = {
        "action": "blocked_action",
        "scope": scope,
        "actor": "user_123"
    }
    await test_client.post("/api/gatekeeper/check", json=check_data)

    # Get blocked actions
    response = await test_client.get(f"/api/gatekeeper/checks/blocked/{scope}")
    assert response.status_code == 200
    checks = response.json()
    assert len(checks) >= 1
    # All should be blocked
    for check in checks:
        assert check["result"] == "block"


# Integration Tests


@pytest.mark.asyncio
async def test_gatekeeper_workflow(test_client):
    """Test complete gatekeeper workflow."""
    # 1. Create policy
    policy_data = {
        "name": "workflow_test_policy",
        "description": "Test workflow policy",
        "condition": {"action": "sensitive_action"},
        "action": "review",
        "severity": "high",
        "scope": "production",
        "active": True
    }
    policy_response = await test_client.post("/api/gatekeeper/policies", json=policy_data)
    assert policy_response.status_code == 201
    policy_id = policy_response.json()["policy_id"]

    # 2. Create risk assessment
    risk_data = {
        "action_type": "sensitive_action",
        "risk_level": "medium",
        "risk_factors": {"impact": "medium"},
        "mitigation": "Review before execution",
        "scope": "production"
    }
    risk_response = await test_client.post("/api/gatekeeper/risks", json=risk_data)
    assert risk_response.status_code == 201

    # 3. Check action
    check_data = {
        "action": "sensitive_action",
        "scope": "production",
        "actor": "user_123",
        "context": {}
    }
    check_response = await test_client.post("/api/gatekeeper/check", json=check_data)
    assert check_response.status_code == 200
    check_result = check_response.json()

    # Should be affected by policy
    assert len(check_result["blocked_policies"]) > 0 or check_result["action"] == "review"

    # 4. Verify check is recorded
    check_id = check_result["check_id"]
    get_check_response = await test_client.get(f"/api/gatekeeper/checks/{check_id}")
    assert get_check_response.status_code == 200

    # 5. Cleanup
    delete_response = await test_client.delete(f"/api/gatekeeper/policies/{policy_id}")
    assert delete_response.status_code == 204
