"""
Governance Rules Engine Tests
"""
import pytest
from uuid import uuid4

from app.models.governance import (
    GovernanceRuleCreate,
    GovernanceRuleUpdate,
    GatekeeperCheckRequest,
    Action,
    Severity,
)


# Rule CRUD Tests


@pytest.mark.asyncio
async def test_create_governance_rule(test_client):
    """Test creating a new governance rule."""
    rule_data = {
        "name": "test_no_deploy_without_snapshot",
        "description": "Block deploy without snapshot",
        "condition": {
            "action_type": "deploy",
            "data_conditions": [
                {"field": "has_snapshot", "operator": "equals", "value": False}
            ]
        },
        "action": "block",
        "severity": "high",
        "scope": "production",
        "enabled": True
    }

    response = await test_client.post("/api/governance/rules", json=rule_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_no_deploy_without_snapshot"
    assert data["action"] == "block"
    assert data["severity"] == "high"
    assert data["enabled"] is True
    assert "rule_id" in data


@pytest.mark.asyncio
async def test_create_duplicate_rule_fails(test_client):
    """Test creating duplicate rule fails."""
    rule_data = {
        "name": "duplicate_test",
        "description": "Test duplicate",
        "condition": {"action_type": "test"},
        "action": "warn",
        "severity": "low",
        "enabled": True
    }

    # Create first rule
    response1 = await test_client.post("/api/governance/rules", json=rule_data)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await test_client.post("/api/governance/rules", json=rule_data)
    assert response2.status_code == 400


@pytest.mark.asyncio
async def test_get_governance_rule(test_client):
    """Test getting a governance rule by ID."""
    rule_data = {
        "name": "get_test_rule",
        "description": "Test get rule",
        "condition": {"action_type": "delete"},
        "action": "review",
        "severity": "medium",
        "enabled": True
    }
    create_response = await test_client.post("/api/governance/rules", json=rule_data)
    rule_id = create_response.json()["rule_id"]

    response = await test_client.get(f"/api/governance/rules/{rule_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["rule_id"] == rule_id
    assert data["name"] == "get_test_rule"


@pytest.mark.asyncio
async def test_list_governance_rules(test_client):
    """Test listing governance rules."""
    # Create multiple rules
    for i in range(3):
        rule_data = {
            "name": f"list_test_rule_{i}",
            "description": f"Test rule {i}",
            "condition": {"action_type": f"action_{i}"},
            "action": "warn",
            "severity": "low",
            "enabled": True
        }
        await test_client.post("/api/governance/rules", json=rule_data)

    response = await test_client.get("/api/governance/rules")

    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 3


@pytest.mark.asyncio
async def test_list_rules_with_filters(test_client):
    """Test listing rules with filters."""
    # Create rules with different severities
    await test_client.post("/api/governance/rules", json={
        "name": "high_severity_rule",
        "description": "High severity",
        "condition": {"action_type": "test"},
        "action": "block",
        "severity": "high",
        "enabled": True
    })

    await test_client.post("/api/governance/rules", json={
        "name": "low_severity_rule",
        "description": "Low severity",
        "condition": {"action_type": "test"},
        "action": "warn",
        "severity": "low",
        "enabled": True
    })

    # Filter by high severity
    response = await test_client.get("/api/governance/rules?severity=high")
    assert response.status_code == 200
    rules = response.json()
    assert all(r["severity"] == "high" for r in rules)


@pytest.mark.asyncio
async def test_update_governance_rule(test_client):
    """Test updating a governance rule."""
    rule_data = {
        "name": "update_test_rule",
        "description": "Original description",
        "condition": {"action_type": "test"},
        "action": "warn",
        "severity": "low",
        "enabled": True
    }
    create_response = await test_client.post("/api/governance/rules", json=rule_data)
    rule_id = create_response.json()["rule_id"]

    update_data = {
        "description": "Updated description",
        "severity": "high"
    }
    response = await test_client.put(f"/api/governance/rules/{rule_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["severity"] == "high"


@pytest.mark.asyncio
async def test_delete_governance_rule(test_client):
    """Test deleting a governance rule."""
    rule_data = {
        "name": "delete_test_rule",
        "description": "Test delete",
        "condition": {"action_type": "test"},
        "action": "warn",
        "severity": "low",
        "enabled": True
    }
    create_response = await test_client.post("/api/governance/rules", json=rule_data)
    rule_id = create_response.json()["rule_id"]

    response = await test_client.delete(f"/api/governance/rules/{rule_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = await test_client.get(f"/api/governance/rules/{rule_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_count_governance_rules(test_client):
    """Test counting governance rules."""
    response = await test_client.get("/api/governance/rules/count")
    assert response.status_code == 200
    assert "count" in response.json()


# Gatekeeper Check Tests


@pytest.mark.asyncio
async def test_gatekeeper_check_allowed(test_client):
    """Test gatekeeper check for allowed action."""
    request_data = {
        "action_type": "read",
        "actor": "user_123",
        "scope": "global",
        "target_data": {}
    }

    response = await test_client.post("/api/governance/gatekeeper/check", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True
    assert data["action"] in ["allow", "warn"]
    assert data["risk_score"] >= 0.0
    assert data["risk_score"] <= 1.0


@pytest.mark.asyncio
async def test_gatekeeper_check_blocked(test_client):
    """Test gatekeeper check for blocked action."""
    # Create blocking rule
    rule_data = {
        "name": "block_deploy_no_snapshot",
        "description": "Block deploy without snapshot",
        "condition": {
            "action_type": "deploy",
            "data_conditions": [
                {"field": "has_snapshot", "operator": "equals", "value": False}
            ]
        },
        "action": "block",
        "severity": "high",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    request_data = {
        "action_type": "deploy",
        "actor": "user_123",
        "scope": "production",
        "target_data": {"has_snapshot": False}
    }

    response = await test_client.post("/api/governance/gatekeeper/check", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert data["action"] == "block"
    assert len(data["triggered_rules"]) > 0


@pytest.mark.asyncio
async def test_gatekeeper_check_with_warning(test_client):
    """Test gatekeeper check that produces a warning."""
    rule_data = {
        "name": "warn_known_failure",
        "description": "Warn about known failures",
        "condition": {
            "action_type": "retry",
            "data_conditions": [
                {"field": "known_failure", "operator": "equals", "value": True}
            ]
        },
        "action": "warn",
        "severity": "medium",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    request_data = {
        "action_type": "retry",
        "actor": "system",
        "scope": "global",
        "target_data": {"known_failure": True}
    }

    response = await test_client.post("/api/governance/gatekeeper/check", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["action"] in ["warn", "review", "block"]
    assert len(data["warnings"]) > 0 or data["risk_score"] > 0


@pytest.mark.asyncio
async def test_gatekeeper_check_with_review(test_client):
    """Test gatekeeper check that requires review."""
    rule_data = {
        "name": "review_production_changes",
        "description": "Review production changes",
        "condition": {
            "scope_pattern": ".*production.*",
            "action_type": "deploy"
        },
        "action": "review",
        "severity": "high",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    request_data = {
        "action_type": "deploy",
        "actor": "user_123",
        "scope": "production",
        "target_data": {}
    }

    response = await test_client.post("/api/governance/gatekeeper/check", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "review"
    assert len(data["alternatives"]) > 0


@pytest.mark.asyncio
async def test_gatekeeper_risk_assessment(test_client):
    """Test gatekeeper risk assessment."""
    request_data = {
        "action_type": "delete",  # High-risk action
        "actor": "user_123",  # Non-system actor
        "scope": "production",  # Production scope
        "target_data": {"size": 50000}  # Large data
    }

    response = await test_client.post("/api/governance/gatekeeper/check", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 0.0
    # Should have higher risk due to action type, actor, and scope
    assert data["risk_score"] > 0.1


@pytest.mark.asyncio
async def test_gatekeeper_alternatives(test_client):
    """Test gatekeeper alternative suggestions."""
    rule_data = {
        "name": "block_delete_without_backup",
        "description": "Block delete without backup",
        "condition": {
            "action_type": "delete",
            "data_conditions": [
                {"field": "has_backup", "operator": "equals", "value": False}
            ]
        },
        "action": "block",
        "severity": "high",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    request_data = {
        "action_type": "delete",
        "actor": "user_123",
        "scope": "production",
        "target_data": {"has_backup": False}
    }

    response = await test_client.post("/api/governance/gatekeeper/check", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert len(data["alternatives"]) > 0
    # Should suggest archiving or backup
    alt_text = " ".join(data["alternatives"]).lower()
    assert any(term in alt_text for term in ["archive", "backup", "export"])


# Condition Evaluation Tests


@pytest.mark.asyncio
async def test_condition_action_type_match(test_client):
    """Test condition evaluation for action type matching."""
    rule_data = {
        "name": "action_type_test",
        "description": "Test action type condition",
        "condition": {"action_type": "specific_action"},
        "action": "review",
        "severity": "low",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    # Should trigger
    request1 = {
        "action_type": "specific_action",
        "actor": "user",
        "scope": "test",
        "target_data": {}
    }
    response1 = await test_client.post("/api/governance/gatekeeper/check", json=request1)
    assert len(response1.json()["triggered_rules"]) > 0

    # Should not trigger
    request2 = {
        "action_type": "other_action",
        "actor": "user",
        "scope": "test",
        "target_data": {}
    }
    response2 = await test_client.post("/api/governance/gatekeeper/check", json=request2)
    assert len(response2.json()["triggered_rules"]) == 0


@pytest.mark.asyncio
async def test_condition_actor_pattern(test_client):
    """Test condition evaluation for actor pattern matching."""
    rule_data = {
        "name": "actor_pattern_test",
        "description": "Test actor pattern",
        "condition": {
            "action_type": "admin_action",
            "actor_pattern": "^admin_.*"
        },
        "action": "allow",
        "severity": "low",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    # Should trigger - admin user
    request1 = {
        "action_type": "admin_action",
        "actor": "admin_123",
        "scope": "global",
        "target_data": {}
    }
    response1 = await test_client.post("/api/governance/gatekeeper/check", json=request1)
    assert len(response1.json()["triggered_rules"]) > 0

    # Should not trigger - regular user
    request2 = {
        "action_type": "admin_action",
        "actor": "user_123",
        "scope": "global",
        "target_data": {}
    }
    response2 = await test_client.post("/api/governance/gatekeeper/check", json=request2)
    assert len(response2.json()["triggered_rules"]) == 0


@pytest.mark.asyncio
async def test_condition_data_equals(test_client):
    """Test condition evaluation for data equals operator."""
    rule_data = {
        "name": "data_equals_test",
        "description": "Test data equals",
        "condition": {
            "action_type": "test",
            "data_conditions": [
                {"field": "status", "operator": "equals", "value": "critical"}
            ]
        },
        "action": "block",
        "severity": "high",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    # Should trigger
    request1 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"status": "critical"}
    }
    response1 = await test_client.post("/api/governance/gatekeeper/check", json=request1)
    assert response1.json()["action"] == "block"

    # Should not trigger
    request2 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"status": "normal"}
    }
    response2 = await test_client.post("/api/governance/gatekeeper/check", json=request2)
    assert response2.json()["action"] != "block"


@pytest.mark.asyncio
async def test_condition_data_contains(test_client):
    """Test condition evaluation for data contains operator."""
    rule_data = {
        "name": "data_contains_test",
        "description": "Test data contains",
        "condition": {
            "action_type": "test",
            "data_conditions": [
                {"field": "message", "operator": "contains", "value": "error"}
            ]
        },
        "action": "warn",
        "severity": "low",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    # Should trigger
    request1 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"message": "This is an error message"}
    }
    response1 = await test_client.post("/api/governance/gatekeeper/check", json=request1)
    assert len(response1.json()["triggered_rules"]) > 0

    # Should not trigger
    request2 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"message": "This is a warning message"}
    }
    response2 = await test_client.post("/api/governance/gatekeeper/check", json=request2)
    assert len(response2.json()["triggered_rules"]) == 0


@pytest.mark.asyncio
async def test_condition_data_greater_than(test_client):
    """Test condition evaluation for data greater_than operator."""
    rule_data = {
        "name": "data_greater_than_test",
        "description": "Test data greater than",
        "condition": {
            "action_type": "test",
            "data_conditions": [
                {"field": "amount", "operator": "greater_than", "value": 1000}
            ]
        },
        "action": "review",
        "severity": "medium",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    # Should trigger
    request1 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"amount": 1500}
    }
    response1 = await test_client.post("/api/governance/gatekeeper/check", json=request1)
    assert len(response1.json()["triggered_rules"]) > 0

    # Should not trigger
    request2 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"amount": 500}
    }
    response2 = await test_client.post("/api/governance/gatekeeper/check", json=request2)
    assert len(response2.json()["triggered_rules"]) == 0


@pytest.mark.asyncio
async def test_condition_data_exists(test_client):
    """Test condition evaluation for data exists operator."""
    rule_data = {
        "name": "data_exists_test",
        "description": "Test data exists",
        "condition": {
            "action_type": "test",
            "data_conditions": [
                {"field": "approval_token", "operator": "exists"}
            ]
        },
        "action": "allow",
        "severity": "low",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    # Should trigger - field exists
    request1 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"approval_token": "abc123"}
    }
    response1 = await test_client.post("/api/governance/gatekeeper/check", json=request1)
    assert len(response1.json()["triggered_rules"]) > 0

    # Should not trigger - field missing
    request2 = {
        "action_type": "test",
        "actor": "user",
        "scope": "test",
        "target_data": {"other_field": "value"}
    }
    response2 = await test_client.post("/api/governance/gatekeeper/check", json=request2)
    assert len(response2.json()["triggered_rules"]) == 0


# Severity and Action Tests


@pytest.mark.asyncio
async def test_severity_levels(test_client):
    """Test different severity levels."""
    for severity in ["low", "medium", "high", "critical"]:
        rule_data = {
            "name": f"severity_{severity}_test",
            "description": f"Test {severity} severity",
            "condition": {"action_type": f"action_{severity}"},
            "action": "block",
            "severity": severity,
            "enabled": True
        }
        response = await test_client.post("/api/governance/rules", json=rule_data)
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_action_types(test_client):
    """Test different action types."""
    for action in ["allow", "warn", "review", "block", "alternative"]:
        rule_data = {
            "name": f"action_{action}_test",
            "description": f"Test {action} action",
            "condition": {"action_type": f"action_{action}"},
            "action": action,
            "severity": "medium",
            "enabled": True
        }
        response = await test_client.post("/api/governance/rules", json=rule_data)
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_list_governance_actions(test_client):
    """Test getting available governance actions."""
    response = await test_client.get("/api/governance/actions")

    assert response.status_code == 200
    actions = response.json()
    assert "allow" in actions
    assert "warn" in actions
    assert "review" in actions
    assert "block" in actions
    assert "alternative" in actions


@pytest.mark.asyncio
async def test_list_governance_severities(test_client):
    """Test getting available severity levels."""
    response = await test_client.get("/api/governance/severities")

    assert response.status_code == 200
    severities = response.json()
    assert "low" in severities
    assert "medium" in severities
    assert "high" in severities
    assert "critical" in severities


# Integration Tests


@pytest.mark.asyncio
async def test_complete_governance_workflow(test_client):
    """Test complete governance workflow."""
    # 1. Create rule
    rule_data = {
        "name": "workflow_test_rule",
        "description": "Test workflow",
        "condition": {
            "action_type": "sensitive_operation",
            "data_conditions": [
                {"field": "approved", "operator": "equals", "value": False}
            ]
        },
        "action": "block",
        "severity": "high",
        "enabled": True
    }
    create_response = await test_client.post("/api/governance/rules", json=rule_data)
    assert create_response.status_code == 201
    rule_id = create_response.json()["rule_id"]

    # 2. Check blocked action
    check_request = {
        "action_type": "sensitive_operation",
        "actor": "user_123",
        "scope": "production",
        "target_data": {"approved": False}
    }
    check_response = await test_client.post("/api/governance/gatekeeper/check", json=check_request)
    assert check_response.status_code == 200
    check_result = check_response.json()
    assert check_result["allowed"] is False
    assert len(check_result["triggered_rules"]) > 0

    # 3. Update rule to warn instead of block
    update_response = await test_client.put(
        f"/api/governance/rules/{rule_id}",
        json={"action": "warn"}
    )
    assert update_response.status_code == 200

    # 4. Check again - should be allowed with warning
    check_response2 = await test_client.post("/api/governance/gatekeeper/check", json=check_request)
    check_result2 = check_response2.json()
    assert check_result2["allowed"] is True  # WARN allows action
    assert check_result2["action"] == "warn"

    # 5. Cleanup
    delete_response = await test_client.delete(f"/api/governance/rules/{rule_id}")
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_multiple_rules_evaluation(test_client):
    """Test evaluation of multiple rules."""
    # Create multiple rules for same action
    await test_client.post("/api/governance/rules", json={
        "name": "multi_rule_1",
        "description": "Low severity rule",
        "condition": {"action_type": "multi_test"},
        "action": "warn",
        "severity": "low",
        "enabled": True
    })

    await test_client.post("/api/governance/rules", json={
        "name": "multi_rule_2",
        "description": "High severity rule",
        "condition": {"action_type": "multi_test"},
        "action": "block",
        "severity": "high",
        "enabled": True
    })

    # Check action - should be blocked by highest severity
    check_request = {
        "action_type": "multi_test",
        "actor": "user",
        "scope": "test",
        "target_data": {}
    }
    response = await test_client.post("/api/governance/gatekeeper/check", json=check_request)

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "block"  # Most restrictive action
    assert len(data["triggered_rules"]) == 2


@pytest.mark.asyncio
async def test_rule_with_no_condition(test_client):
    """Test rule with empty condition (matches everything)."""
    rule_data = {
        "name": "catch_all_rule",
        "description": "Catches all actions",
        "condition": {},
        "action": "warn",
        "severity": "low",
        "enabled": True
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    # Should trigger for any action
    check_request = {
        "action_type": "any_action",
        "actor": "user",
        "scope": "any_scope",
        "target_data": {}
    }
    response = await test_client.post("/api/governance/gatekeeper/check", json=check_request)

    assert response.status_code == 200
    data = response.json()
    assert len(data["triggered_rules"]) > 0


@pytest.mark.asyncio
async def test_disabled_rule_not_evaluated(test_client):
    """Test that disabled rules are not evaluated."""
    rule_data = {
        "name": "disabled_test_rule",
        "description": "This should not trigger",
        "condition": {"action_type": "test_action"},
        "action": "block",
        "severity": "high",
        "enabled": False  # Disabled
    }
    await test_client.post("/api/governance/rules", json=rule_data)

    check_request = {
        "action_type": "test_action",
        "actor": "user",
        "scope": "test",
        "target_data": {}
    }
    response = await test_client.post("/api/governance/gatekeeper/check", json=check_request)

    assert response.status_code == 200
    data = response.json()
    assert len(data["triggered_rules"]) == 0  # Should not trigger
    assert data["action"] == "allow"  # Should be allowed


@pytest.mark.asyncio
async def test_scope_filtering(test_client):
    """Test scope-based rule filtering."""
    # Create rules with different scopes
    await test_client.post("/api/governance/rules", json={
        "name": "production_rule",
        "description": "Production only",
        "condition": {"action_type": "deploy"},
        "action": "review",
        "severity": "high",
        "scope": "production",
        "enabled": True
    })

    await test_client.post("/api/governance/rules", json={
        "name": "development_rule",
        "description": "Development only",
        "condition": {"action_type": "deploy"},
        "action": "allow",
        "severity": "low",
        "scope": "development",
        "enabled": True
    })

    # Production deploy should be reviewed
    prod_request = {
        "action_type": "deploy",
        "actor": "user",
        "scope": "production",
        "target_data": {}
    }
    prod_response = await test_client.post("/api/governance/gatekeeper/check", json=prod_request)
    assert prod_response.json()["action"] == "review"

    # Development deploy should be allowed
    dev_request = {
        "action_type": "deploy",
        "actor": "user",
        "scope": "development",
        "target_data": {}
    }
    dev_response = await test_client.post("/api/governance/gatekeeper/check", json=dev_request)
    assert dev_response.json()["action"] == "allow"
