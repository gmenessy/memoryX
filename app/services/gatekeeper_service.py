"""
Gatekeeper Service - Business Logic Layer

The Gatekeeper is the most critical component.
Before ANY action, it checks: Is this action sensible?

Checks:
- Policies
- Risks
- Past failures
- Conflicts
- Scope
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gatekeeper import (
    PolicyDB,
    RiskAssessmentDB,
    GatekeeperCheckDB,
    Policy,
    PolicyCreate,
    PolicyUpdate,
    RiskAssessment,
    RiskAssessmentCreate,
    GatekeeperCheck,
    GatekeeperCheckCreate,
    GatekeeperDecision,
    GatekeeperAction,
    RiskLevel,
    PolicySeverity,
)
from app.repositories.gatekeeper_repository import GatekeeperRepository


class GatekeeperService:
    """
    Service for Gatekeeper operations.
    Implements the business logic for action validation and governance.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GatekeeperRepository(session)

    # Policy Management

    async def create_policy(self, policy_create: PolicyCreate) -> Policy:
        """Create a new governance policy."""
        # Check if policy name already exists
        existing = await self.repo.get_policy_by_name(policy_create.name)
        if existing:
            raise ValueError(f"Policy with name '{policy_create.name}' already exists")

        policy_db = PolicyDB(
            name=policy_create.name,
            description=policy_create.description,
            condition=policy_create.condition,
            action=policy_create.action,
            severity=policy_create.severity,
            scope=policy_create.scope,
            active=policy_create.active
        )

        created = await self.repo.create_policy(policy_db)
        return Policy.model_validate(created)

    async def get_policy(self, policy_id: UUID) -> Policy | None:
        """Get policy by ID."""
        policy = await self.repo.get_policy(policy_id)
        return Policy.model_validate(policy) if policy else None

    async def list_policies(
        self,
        scope: str | None = None,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> list[Policy]:
        """List policies with optional filters."""
        policies = await self.repo.list_policies(scope, active_only, limit, offset)
        return [Policy.model_validate(p) for p in policies]

    async def update_policy(self, policy_id: UUID, policy_update: PolicyUpdate) -> Policy | None:
        """Update existing policy."""
        policy = await self.repo.get_policy(policy_id)
        if not policy:
            return None

        if policy_update.description is not None:
            policy.description = policy_update.description
        if policy_update.condition is not None:
            policy.condition = policy_update.condition
        if policy_update.action is not None:
            policy.action = policy_update.action
        if policy_update.severity is not None:
            policy.severity = policy_update.severity
        if policy_update.active is not None:
            policy.active = policy_update.active

        updated = await self.repo.update_policy(policy)
        return Policy.model_validate(updated)

    async def delete_policy(self, policy_id: UUID) -> bool:
        """Delete policy by ID."""
        return await self.repo.delete_policy(policy_id)

    async def count_policies(
        self,
        scope: str | None = None,
        active_only: bool = False
    ) -> int:
        """Count policies with optional filters."""
        return await self.repo.count_policies(scope, active_only)

    async def activate_policy(self, policy_id: UUID) -> Policy | None:
        """Activate a policy."""
        policy = await self.repo.get_policy(policy_id)
        if not policy:
            return None

        policy.active = True
        updated = await self.repo.update_policy(policy)
        return Policy.model_validate(updated)

    async def deactivate_policy(self, policy_id: UUID) -> Policy | None:
        """Deactivate a policy."""
        policy = await self.repo.get_policy(policy_id)
        if not policy:
            return None

        policy.active = False
        updated = await self.repo.update_policy(policy)
        return Policy.model_validate(updated)

    # Risk Assessment Management

    async def create_risk_assessment(self, risk_create: RiskAssessmentCreate) -> RiskAssessment:
        """Create a new risk assessment."""
        risk_db = RiskAssessmentDB(
            action_type=risk_create.action_type,
            risk_level=risk_create.risk_level,
            risk_factors=risk_create.risk_factors,
            mitigation=risk_create.mitigation,
            scope=risk_create.scope
        )

        created = await self.repo.create_risk_assessment(risk_db)
        return RiskAssessment.model_validate(created)

    async def get_risk_assessment(self, assessment_id: UUID) -> RiskAssessment | None:
        """Get risk assessment by ID."""
        risk = await self.repo.get_risk_assessment(assessment_id)
        return RiskAssessment.model_validate(risk) if risk else None

    async def list_risk_assessments(
        self,
        action_type: str | None = None,
        scope: str | None = None,
        risk_level: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[RiskAssessment]:
        """List risk assessments with optional filters."""
        risks = await self.repo.list_risk_assessments(action_type, scope, risk_level, limit, offset)
        return [RiskAssessment.model_validate(r) for r in risks]

    async def delete_risk_assessment(self, assessment_id: UUID) -> bool:
        """Delete risk assessment by ID."""
        return await self.repo.delete_risk_assessment(assessment_id)

    async def count_risk_assessments(
        self,
        action_type: str | None = None,
        scope: str | None = None,
        risk_level: str | None = None
    ) -> int:
        """Count risk assessments with optional filters."""
        return await self.repo.count_risk_assessments(action_type, scope, risk_level)

    # CORE: Gatekeeper Check Logic

    async def check_action(
        self,
        action: str,
        scope: str,
        actor: str,
        context: dict[str, Any] | None = None
    ) -> GatekeeperDecision:
        """
        Check if an action should be allowed.

        This is the CORE function of the Gatekeeper.
        Before ANY action, this should be called.

        Checks:
        1. Active policies for this scope
        2. Risk assessments for this action
        3. Past failures (from events)
        4. Conflicts (optional, based on context)

        Returns: GatekeeperDecision with action to take
        """
        if context is None:
            context = {}

        # Get active policies for scope
        active_policies = await self.repo.get_active_policies_for_scope(scope)

        # Get risk assessments for action
        risks = await self.repo.get_risks_for_action(action, scope)

        # Evaluate policies
        matched_policies = []
        policy_result = GatekeeperAction.ALLOW
        policy_reason = "No policies matched"
        warnings = []

        for policy in active_policies:
            if self._matches_condition(policy.condition, action, context):
                matched_policies.append(policy)

                # Determine severity-based action
                if policy.severity in ["critical", "high"]:
                    if policy.action == "block":
                        policy_result = GatekeeperAction.BLOCK
                        policy_reason = f"Blocked by policy: {policy.name}"
                    elif policy.action == "review":
                        if policy_result != GatekeeperAction.BLOCK:
                            policy_result = GatekeeperAction.REVIEW
                            policy_reason = f"Review required by policy: {policy.name}"
                elif policy.severity == "medium":
                    if policy.action == "warn" and policy_result == GatekeeperAction.ALLOW:
                        policy_result = GatekeeperAction.WARN
                        policy_reason = f"Warning from policy: {policy.name}"
                        warnings.append(policy.description)

        # Evaluate risks
        risk_level = RiskLevel.NONE
        if risks:
            highest_risk = max(risks, key=lambda r: self._risk_weight(r.risk_level))
            risk_level = highest_risk.risk_level

            # High risk can override allow
            if risk_level in ["high", "severe"]:
                if policy_result == GatekeeperAction.ALLOW:
                    policy_result = GatekeeperAction.WARN
                    warnings.append(f"High risk action: {highest_risk.risk_level}")

        # Calculate confidence
        confidence = self._calculate_confidence(matched_policies, risks, context)

        # Determine final action
        final_action = policy_result
        allowed = final_action in [GatekeeperAction.ALLOW, GatekeeperAction.WARN]

        # Create check record
        check_db = GatekeeperCheckDB(
            action=action,
            result=final_action.value,
            reason=policy_reason,
            policies_matched=[p.policy_id for p in matched_policies],
            risks_found=[r.assessment_id for r in risks],
            conflicts=self._detect_conflicts(context),
            alternative_suggested=self._suggest_alternative(action, context),
            confidence=confidence,
            scope=scope,
            actor=actor
        )

        await self.repo.create_check(check_db)

        return GatekeeperDecision(
            allowed=allowed,
            action=final_action,
            reason=policy_reason,
            warnings=warnings,
            blocked_policies=[p.policy_id for p in matched_policies if p.action == "block"],
            risks=[r.assessment_id for r in risks],
            alternative=self._suggest_alternative(action, context),
            confidence=confidence,
            check_id=check_db.check_id
        )

    def _matches_condition(self, condition: dict[str, Any], action: str, context: dict[str, Any]) -> bool:
        """
        Check if an action and context match a policy condition.

        Simple matching for now - can be extended with more complex logic.
        """
        # Check action match
        if "action" in condition:
            if condition["action"] != action:
                return False

        # Check other conditions against context
        for key, value in condition.items():
            if key == "action":
                continue
            if key not in context:
                if value is True:  # Condition requires this to be true
                    return False
                continue
            if context[key] != value:
                return False

        return True

    def _risk_weight(self, risk_level: str) -> int:
        """Get numeric weight for risk level."""
        weights = {
            "none": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "severe": 4
        }
        return weights.get(risk_level, 0)

    def _calculate_confidence(
        self,
        matched_policies: list[PolicyDB],
        risks: list[RiskAssessmentDB],
        context: dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for the decision.

        Higher confidence when:
        - Clear policy match
        - Low risk
        - Sufficient context
        """
        confidence = 0.5  # Base confidence

        if matched_policies:
            confidence += 0.2

        if not risks or all(r.risk_level in ["none", "low"] for r in risks):
            confidence += 0.2

        if context:
            confidence += 0.1

        return min(confidence, 1.0)

    def _detect_conflicts(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Detect conflicts in the context.

        For now, simple conflict detection.
        Can be extended with more complex logic.
        """
        conflicts = {}

        # Check for scope conflicts
        if "scope" in context and "conflicting_scope" in context:
            conflicts["scope"] = {
                "current": context["scope"],
                "conflicting": context["conflicting_scope"]
            }

        # Check for memory conflicts
        if "has_conflict" in context and context["has_conflict"]:
            conflicts["memory"] = context.get("conflict_details", {})

        return conflicts

    def _suggest_alternative(self, action: str, context: dict[str, Any]) -> str | None:
        """
        Suggest alternative action if needed.

        Simple suggestions for common actions.
        """
        alternatives = {
            "deploy": "Create a snapshot before deploying",
            "delete": "Archive instead of delete",
            "overwrite": "Create a new version instead",
            "merge": "Review conflicts before merging"
        }

        return alternatives.get(action)

    # Check History and Statistics

    async def get_check(self, check_id: UUID) -> GatekeeperCheck | None:
        """Get check by ID."""
        check = await self.repo.get_check(check_id)
        return GatekeeperCheck.model_validate(check) if check else None

    async def list_checks(
        self,
        action: str | None = None,
        result: str | None = None,
        scope: str | None = None,
        actor: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GatekeeperCheck]:
        """List checks with optional filters."""
        checks = await self.repo.list_checks(action, result, scope, actor, limit, offset)
        return [GatekeeperCheck.model_validate(c) for c in checks]

    async def count_checks(
        self,
        action: str | None = None,
        result: str | None = None,
        scope: str | None = None,
        actor: str | None = None
    ) -> int:
        """Count checks with optional filters."""
        return await self.repo.count_checks(action, result, scope, actor)

    async def get_statistics(
        self,
        scope: str | None = None,
        actor: str | None = None
    ) -> dict[str, Any]:
        """Get gatekeeper statistics."""
        return await self.repo.get_check_statistics(scope, actor)

    async def get_actor_history(self, actor: str, limit: int = 50) -> list[GatekeeperCheck]:
        """Get recent checks for a specific actor."""
        checks = await self.repo.get_checks_by_actor(actor, limit)
        return [GatekeeperCheck.model_validate(c) for c in checks]

    async def get_blocked_actions(self, scope: str, limit: int = 100) -> list[GatekeeperCheck]:
        """Get recently blocked actions for a scope."""
        checks = await self.repo.get_blocked_checks(scope, limit)
        return [GatekeeperCheck.model_validate(c) for c in checks]
