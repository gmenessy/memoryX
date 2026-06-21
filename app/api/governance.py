"""
Governance API Routes - REST Endpoints for Memory Gatekeeper Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.governance import (
    GovernanceRuleCreate,
    GovernanceRuleUpdate,
    GovernanceRuleResponse,
    GatekeeperCheckRequest,
    GatekeeperCheckResponse,
    Action,
    Severity
)
from app.services.gatekeeper_service import GatekeeperService

router = APIRouter(prefix="/api/governance", tags=["Governance"])


@router.post("/rules", response_model=GovernanceRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_governance_rule(
    rule_data: GovernanceRuleCreate,
    session: AsyncSession = Depends(get_db_session)
) -> GovernanceRuleResponse:
    """
    Create a new governance rule.

    Governance rules define executable policies for memory operations.
    Rules are evaluated by the Memory Gatekeeper before actions are executed.

    - **name**: Unique rule name
    - **description**: Rule description
    - **condition**: Rule condition logic (JSON)
    - **action**: Action to take (allow, warn, review, block, alternative)
    - **severity**: Severity level (low, medium, high, critical)
    - **scope**: Rule scope (optional, null means global)
    - **enabled**: Whether rule is enabled
    """
    try:
        service = GatekeeperService(session)
        return await service.create_rule(rule_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/rules/{rule_id}", response_model=GovernanceRuleResponse)
async def get_governance_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> GovernanceRuleResponse:
    """
    Get a specific governance rule by ID.
    """
    service = GatekeeperService(session)
    rule = await service.get_rule(rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Governance rule {rule_id} not found"
        )

    return rule


@router.get("/rules", response_model=list[GovernanceRuleResponse])
async def list_governance_rules(
    enabled_only: bool = Query(True, description="Only return enabled rules"),
    scope: str | None = Query(None, description="Filter by scope"),
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[GovernanceRuleResponse]:
    """
    List governance rules with optional filtering.

    Results are ordered by severity (critical first) then name.
    """
    service = GatekeeperService(session)
    return await service.list_rules(
        enabled_only=enabled_only,
        scope=scope,
        severity=severity,
        limit=limit,
        offset=offset
    )


@router.put("/rules/{rule_id}", response_model=GovernanceRuleResponse)
async def update_governance_rule(
    rule_id: UUID,
    update_data: GovernanceRuleUpdate,
    session: AsyncSession = Depends(get_db_session)
) -> GovernanceRuleResponse:
    """
    Update a governance rule.

    Only provided fields are updated (partial update).
    """
    service = GatekeeperService(session)
    rule = await service.update_rule(rule_id, update_data)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Governance rule {rule_id} not found"
        )

    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_governance_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Delete a governance rule.

    Use with caution - this operation cannot be undone.
    """
    service = GatekeeperService(session)
    success = await service.delete_rule(rule_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Governance rule {rule_id} not found"
        )


@router.get("/rules/count", response_model=dict)
async def count_governance_rules(
    enabled_only: bool = Query(True, description="Only count enabled rules"),
    scope: str | None = Query(None, description="Filter by scope"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Count governance rules matching filters.

    Returns the total count (useful for pagination).
    """
    service = GatekeeperService(session)
    count = await service.count_rules(
        enabled_only=enabled_only,
        scope=scope
    )

    return {"count": count}


@router.post("/gatekeeper/check", response_model=GatekeeperCheckResponse)
async def gatekeeper_check(
    request: GatekeeperCheckRequest,
    session: AsyncSession = Depends(get_db_session)
) -> GatekeeperCheckResponse:
    """
    Validate an action against governance rules.

    The Memory Gatekeeper evaluates actions against all applicable
    governance rules and provides recommendations.

    - **action_type**: Type of action to validate
    - **actor**: Who is performing the action
    - **scope**: Action scope/context
    - **target_data**: Target data for the action
    - **metadata**: Additional metadata

    Returns validation result with:
    - **allowed**: Whether action is allowed
    - **action**: Recommended action (allow/warn/review/block/alternative)
    - **reason**: Reason for the decision
    - **triggered_rules**: Rules that were triggered
    - **risk_score**: Calculated risk score (0-1)
    - **alternatives**: Alternative approaches if blocked
    - **warnings**: Warnings for the action
    """
    service = GatekeeperService(session)
    return await service.validate_action(request)


@router.get("/actions", response_model=list[str])
async def list_governance_actions() -> list[str]:
    """
    Get available governance actions.

    Returns the list of valid governance actions.
    """
    return [action.value for action in Action]


@router.get("/severities", response_model=list[str])
async def list_governance_severities() -> list[str]:
    """
    Get available severity levels.

    Returns the list of valid severity levels.
    """
    return [severity.value for severity in Severity]