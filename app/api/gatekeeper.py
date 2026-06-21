"""
Gatekeeper API Routes - REST Endpoints for Memory Gatekeeper Operations

The Gatekeeper is the most critical component.
Before ANY action, it checks: Is this action sensible?
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.gatekeeper import (
    Policy,
    PolicyCreate,
    PolicyUpdate,
    RiskAssessment,
    RiskAssessmentCreate,
    GatekeeperCheck,
    GatekeeperCheckCreate,
    GatekeeperDecision,
    POLICY_ACTIONS,
    SEVERITY_LEVELS,
    RISK_LEVELS,
)
from app.services.gatekeeper_service import GatekeeperService

router = APIRouter(prefix="/api/gatekeeper", tags=["Gatekeeper"])


# Policy Endpoints


@router.post("/policies", response_model=Policy, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_data: PolicyCreate,
    session: AsyncSession = Depends(get_db_session)
) -> Policy:
    """
    Create a new governance policy.

    Policies define executable rules for memory operations.
    The Gatekeeper evaluates policies before actions are executed.

    - **name**: Unique policy name
    - **description**: Policy description
    - **condition**: Policy condition logic (JSON)
    - **action**: Action to take (allow, warn, review, block, alternative)
    - **severity**: Severity level (info, low, medium, high, critical)
    - **scope**: Policy scope
    - **active**: Whether policy is active
    """
    try:
        service = GatekeeperService(session)
        return await service.create_policy(policy_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> Policy:
    """Get a specific policy by ID."""
    service = GatekeeperService(session)
    policy = await service.get_policy(policy_id)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found"
        )

    return policy


@router.get("/policies", response_model=list[Policy])
async def list_policies(
    scope: str | None = Query(None, description="Filter by scope"),
    active_only: bool = Query(False, description="Only return active policies"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[Policy]:
    """
    List policies with optional filtering.

    Results are ordered by creation date (newest first).
    """
    service = GatekeeperService(session)
    return await service.list_policies(
        scope=scope,
        active_only=active_only,
        limit=limit,
        offset=offset
    )


@router.put("/policies/{policy_id}", response_model=Policy)
async def update_policy(
    policy_id: UUID,
    update_data: PolicyUpdate,
    session: AsyncSession = Depends(get_db_session)
) -> Policy:
    """
    Update a policy.

    Only provided fields are updated (partial update).
    """
    service = GatekeeperService(session)
    policy = await service.update_policy(policy_id, update_data)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found"
        )

    return policy


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Delete a policy.

    Use with caution - this operation cannot be undone.
    """
    service = GatekeeperService(session)
    success = await service.delete_policy(policy_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found"
        )


@router.post("/policies/{policy_id}/activate", response_model=Policy)
async def activate_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> Policy:
    """Activate a policy."""
    service = GatekeeperService(session)
    policy = await service.activate_policy(policy_id)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found"
        )

    return policy


@router.post("/policies/{policy_id}/deactivate", response_model=Policy)
async def deactivate_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> Policy:
    """Deactivate a policy."""
    service = GatekeeperService(session)
    policy = await service.deactivate_policy(policy_id)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found"
        )

    return policy


@router.get("/policies/count", response_model=dict)
async def count_policies(
    scope: str | None = Query(None, description="Filter by scope"),
    active_only: bool = Query(False, description="Only count active policies"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Count policies matching filters.

    Returns the total count (useful for pagination).
    """
    service = GatekeeperService(session)
    count = await service.count_policies(scope=scope, active_only=active_only)

    return {"count": count}


# Risk Assessment Endpoints


@router.post("/risks", response_model=RiskAssessment, status_code=status.HTTP_201_CREATED)
async def create_risk_assessment(
    risk_data: RiskAssessmentCreate,
    session: AsyncSession = Depends(get_db_session)
) -> RiskAssessment:
    """
    Create a new risk assessment.

    Risk assessments define potential risks for actions.
    The Gatekeeper uses these to evaluate action safety.

    - **action_type**: Type of action being assessed
    - **risk_level**: Risk level (none, low, medium, high, severe)
    - **risk_factors**: Risk factors (JSON)
    - **mitigation**: Mitigation strategy
    - **scope**: Assessment scope
    """
    service = GatekeeperService(session)
    return await service.create_risk_assessment(risk_data)


@router.get("/risks/{assessment_id}", response_model=RiskAssessment)
async def get_risk_assessment(
    assessment_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> RiskAssessment:
    """Get a specific risk assessment by ID."""
    service = GatekeeperService(session)
    risk = await service.get_risk_assessment(assessment_id)

    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment {assessment_id} not found"
        )

    return risk


@router.get("/risks", response_model=list[RiskAssessment])
async def list_risk_assessments(
    action_type: str | None = Query(None, description="Filter by action type"),
    scope: str | None = Query(None, description="Filter by scope"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[RiskAssessment]:
    """
    List risk assessments with optional filtering.

    Results are ordered by creation date (newest first).
    """
    service = GatekeeperService(session)
    return await service.list_risk_assessments(
        action_type=action_type,
        scope=scope,
        risk_level=risk_level,
        limit=limit,
        offset=offset
    )


@router.delete("/risks/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_assessment(
    assessment_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """Delete a risk assessment."""
    service = GatekeeperService(session)
    success = await service.delete_risk_assessment(assessment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment {assessment_id} not found"
        )


@router.get("/risks/count", response_model=dict)
async def count_risk_assessments(
    action_type: str | None = Query(None, description="Filter by action type"),
    scope: str | None = Query(None, description="Filter by scope"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Count risk assessments matching filters.

    Returns the total count (useful for pagination).
    """
    service = GatekeeperService(session)
    count = await service.count_risk_assessments(
        action_type=action_type,
        scope=scope,
        risk_level=risk_level
    )

    return {"count": count}


# CORE: Gatekeeper Check Endpoint


@router.post("/check", response_model=GatekeeperDecision)
async def check_action(
    check_data: GatekeeperCheckCreate,
    session: AsyncSession = Depends(get_db_session)
) -> GatekeeperDecision:
    """
    Validate an action against governance policies and risk assessments.

    This is the CORE Gatekeeper endpoint.
    Before ANY action, this should be called.

    The Gatekeeper evaluates:
    - Active policies for this scope
    - Risk assessments for this action
    - Past failures
    - Conflicts

    Returns validation result with:
    - **allowed**: Whether action is allowed
    - **action**: Recommended action (allow/warn/review/block/alternative)
    - **reason**: Reason for the decision
    - **warnings**: Warning messages
    - **blocked_policies**: Policies that blocked the action
    - **risks**: Risk assessments found
    - **alternative**: Suggested alternative action
    - **confidence**: Confidence score (0-1)
    - **check_id**: Reference check ID for audit trail

    Example request:
    ```json
    {
        "action": "deploy",
        "scope": "production",
        "actor": "user_123",
        "context": {"has_snapshot": false}
    }
    ```
    """
    service = GatekeeperService(session)
    return await service.check_action(
        action=check_data.action,
        scope=check_data.scope,
        actor=check_data.actor,
        context=check_data.context
    )


# Check History Endpoints


@router.get("/checks/{check_id}", response_model=GatekeeperCheck)
async def get_check(
    check_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> GatekeeperCheck:
    """Get a specific check by ID."""
    service = GatekeeperService(session)
    check = await service.get_check(check_id)

    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check {check_id} not found"
        )

    return check


@router.get("/checks", response_model=list[GatekeeperCheck])
async def list_checks(
    action: str | None = Query(None, description="Filter by action"),
    result: str | None = Query(None, description="Filter by result"),
    scope: str | None = Query(None, description="Filter by scope"),
    actor: str | None = Query(None, description="Filter by actor"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[GatekeeperCheck]:
    """
    List gatekeeper checks with optional filtering.

    Results are ordered by check date (newest first).
    """
    service = GatekeeperService(session)
    return await service.list_checks(
        action=action,
        result=result,
        scope=scope,
        actor=actor,
        limit=limit,
        offset=offset
    )


@router.get("/checks/count", response_model=dict)
async def count_checks(
    action: str | None = Query(None, description="Filter by action"),
    result: str | None = Query(None, description="Filter by result"),
    scope: str | None = Query(None, description="Filter by scope"),
    actor: str | None = Query(None, description="Filter by actor"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Count checks matching filters.

    Returns the total count (useful for pagination).
    """
    service = GatekeeperService(session)
    count = await service.count_checks(
        action=action,
        result=result,
        scope=scope,
        actor=actor
    )

    return {"count": count}


@router.get("/checks/actor/{actor}", response_model=list[GatekeeperCheck])
async def get_actor_history(
    actor: str,
    limit: int = Query(50, ge=1, le=500, description="Max results (1-500)"),
    session: AsyncSession = Depends(get_db_session)
) -> list[GatekeeperCheck]:
    """
    Get recent checks for a specific actor.

    Useful for auditing actor behavior.
    """
    service = GatekeeperService(session)
    return await service.get_actor_history(actor, limit=limit)


@router.get("/checks/blocked/{scope}", response_model=list[GatekeeperCheck])
async def get_blocked_actions(
    scope: str,
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    session: AsyncSession = Depends(get_db_session)
) -> list[GatekeeperCheck]:
    """
    Get recently blocked actions for a scope.

    Useful for reviewing what has been blocked.
    """
    service = GatekeeperService(session)
    return await service.get_blocked_actions(scope, limit=limit)


@router.get("/statistics", response_model=dict)
async def get_statistics(
    scope: str | None = Query(None, description="Filter by scope"),
    actor: str | None = Query(None, description="Filter by actor"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get gatekeeper statistics.

    Returns:
    - **total**: Total checks performed
    - **allowed**: Number of allowed actions
    - **blocked**: Number of blocked actions
    - **warnings**: Number of warnings
    - **reviews**: Number of reviews required
    - **average_confidence**: Average confidence score
    """
    service = GatekeeperService(session)
    return await service.get_statistics(scope=scope, actor=actor)


# Metadata Endpoints


@router.get("/types", response_model=dict)
async def get_types() -> dict:
    """
    Get available types for Gatekeeper.

    Returns:
    - **actions**: Available policy actions
    - **severities**: Available severity levels
    - **risk_levels**: Available risk levels
    """
    return {
        "actions": POLICY_ACTIONS,
        "severities": SEVERITY_LEVELS,
        "risk_levels": RISK_LEVELS
    }
