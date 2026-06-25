"""
Governance Service - Business Logic Layer for Governance Rules Engine

The Governance Rules Engine provides executable memory (rules that govern actions).
Rules are evaluated by the Gatekeeper before actions are executed.
"""
from datetime import datetime
from typing import Any
from uuid import UUID
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    LARGE_PAYLOAD_THRESHOLD,
    RISK_SCORE_CRITICAL,
    RISK_SCORE_HIGH,
    RISK_SCORE_MEDIUM,
)
from app.exceptions import ConflictError, ValidationError
from app.logging_config import get_logger
from app.models.governance import (
    Action,
    GovernanceRuleCreate,
    GovernanceRuleResponse,
    GovernanceRuleUpdate,
    GatekeeperCheckRequest,
    GatekeeperCheckResponse,
    RiskAssessment,
    Severity,
)
from app.repositories.governance_repository import GovernanceRepository

logger = get_logger(__name__)


class GovernanceService:
    """
    Service for Governance Rules Engine operations.
    Implements the business logic for rule management and validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = GovernanceRepository(session)

    # Rule Management

    async def create_rule(self, rule_data: GovernanceRuleCreate) -> GovernanceRuleResponse:
        """Create a new governance rule."""
        # Check if rule name already exists
        existing = await self.repo.get_rule_by_name(rule_data.name)
        if existing:
            raise ConflictError(
                f"Rule with name '{rule_data.name}' already exists",
                details={"rule_name": rule_data.name, "existing_rule_id": str(existing.rule_id)}
            )

        return await self.repo.create_rule(rule_data)

    async def get_rule(self, rule_id: UUID) -> GovernanceRuleResponse | None:
        """Get rule by ID."""
        return await self.repo.get_rule(rule_id)

    async def get_rule_by_name(self, name: str) -> GovernanceRuleResponse | None:
        """Get rule by name."""
        return await self.repo.get_rule_by_name(name)

    async def list_rules(
        self,
        enabled_only: bool = True,
        scope: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GovernanceRuleResponse]:
        """List governance rules with optional filtering."""
        return await self.repo.list_rules(
            enabled_only=enabled_only,
            scope=scope,
            severity=severity,
            limit=limit,
            offset=offset
        )

    async def update_rule(self, rule_id: UUID, update_data: GovernanceRuleUpdate) -> GovernanceRuleResponse | None:
        """Update a governance rule."""
        return await self.repo.update_rule(rule_id, update_data)

    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a governance rule."""
        return await self.repo.delete_rule(rule_id)

    async def count_rules(
        self,
        enabled_only: bool = True,
        scope: str | None = None
    ) -> int:
        """Count governance rules."""
        return await self.repo.count_rules(
            enabled_only=enabled_only,
            scope=scope
        )

    # Rule Evaluation

    async def evaluate_rules(
        self,
        request: GatekeeperCheckRequest,
        rules: list[GovernanceRuleResponse] | None = None
    ) -> tuple[GatekeeperCheckResponse, RiskAssessment]:
        """
        Evaluate governance rules against an action request.

        This is the CORE function of the Governance Rules Engine.
        It evaluates all applicable rules and provides recommendations.

        Args:
            request: The action validation request
            rules: Optional list of rules to evaluate (if None, fetches applicable)

        Returns:
            Tuple of (check_response, risk_assessment)
        """
        # Get applicable rules if not provided
        if rules is None:
            rules = await self.repo.get_applicable_rules(
                action_type=request.action_type,
                scope=request.scope,
                enabled_only=True
            )

        # Evaluate rules and find triggered ones
        triggered_rules = []
        highest_severity = Severity.LOW
        recommended_action = Action.ALLOW

        for rule in rules:
            if self._evaluate_condition(rule.condition, request):
                triggered_rules.append({
                    "rule_id": str(rule.rule_id),
                    "name": rule.name,
                    "description": rule.description,
                    "action": rule.action,
                    "severity": rule.severity
                })

                # Determine highest severity
                rule_severity = Severity(rule.severity)
                if self._severity_compare(rule_severity, highest_severity) > 0:
                    highest_severity = rule_severity

                # Use the most restrictive action
                rule_action = Action(rule.action)
                if self._action_compare(rule_action, recommended_action) > 0:
                    recommended_action = rule_action

        # Calculate risk assessment
        risk_assessment = await self._assess_risk(request, triggered_rules)

        # Determine if action is allowed
        allowed = recommended_action in [Action.ALLOW, Action.WARN]

        # Generate response
        warnings = []
        alternatives = []

        if recommended_action == Action.WARN:
            warnings.append(f"Action triggers {len(triggered_rules)} governance rule(s)")
        elif recommended_action == Action.REVIEW:
            warnings.append("Action requires review before proceeding")
            alternatives.append("Request review from authorized personnel")
        elif recommended_action == Action.BLOCK:
            warnings.append("Action is blocked by governance rules")
            alternatives = await self._generate_alternatives(request, triggered_rules)
        elif recommended_action == Action.ALTERNATIVE:
            warnings.append("Alternative approach recommended")
            alternatives = await self._generate_alternatives(request, triggered_rules)

        response = GatekeeperCheckResponse(
            allowed=allowed,
            action=recommended_action.value,
            reason=self._generate_reason(triggered_rules, highest_severity),
            triggered_rules=triggered_rules,
            risk_score=risk_assessment.risk_score,
            alternatives=alternatives,
            warnings=warnings
        )

        return response, risk_assessment

    def _evaluate_condition(
        self,
        condition: dict[str, Any],
        request: GatekeeperCheckRequest
    ) -> bool:
        """
        Evaluate a rule condition against the request.

        Supports:
        - Action type matching
        - Actor pattern matching (regex)
        - Scope pattern matching (regex)
        - Data conditions (equals, not_equals, contains, greater_than, less_than)

        Args:
            condition: Rule condition logic
            request: Validation request

        Returns:
            True if condition is met
        """
        if not condition:
            return True

        # Check action type match
        if "action_type" in condition:
            if condition["action_type"] != request.action_type:
                return False

        # Check actor patterns (regex support)
        if "actor_pattern" in condition:
            import re
            pattern = condition["actor_pattern"]
            if not re.search(pattern, request.actor):
                return False

        # Check scope patterns (regex support)
        if "scope_pattern" in condition:
            import re
            pattern = condition["scope_pattern"]
            if not re.search(pattern, request.scope):
                return False

        # Check data conditions
        if "data_conditions" in condition:
            for data_cond in condition["data_conditions"]:
                field = data_cond.get("field")
                operator = data_cond.get("operator")
                value = data_cond.get("value")

                if field not in request.target_data:
                    if operator != "not_equals":
                        return False
                    continue

                target_value = request.target_data[field]

                if operator == "equals":
                    if target_value != value:
                        return False
                elif operator == "not_equals":
                    if target_value == value:
                        return False
                elif operator == "contains":
                    if value not in str(target_value):
                        return False
                elif operator == "greater_than":
                    try:
                        if not float(target_value) > float(value):
                            return False
                    except (ValueError, TypeError):
                        return False
                elif operator == "less_than":
                    try:
                        if not float(target_value) < float(value):
                            return False
                    except (ValueError, TypeError):
                        return False
                elif operator == "exists":
                    if field not in request.target_data:
                        return False
                elif operator == "not_exists":
                    if field in request.target_data:
                        return False

        # Check metadata conditions
        if "metadata_conditions" in condition:
            for meta_cond in condition["metadata_conditions"]:
                field = meta_cond.get("field")
                operator = meta_cond.get("operator")
                value = meta_cond.get("value")

                if field not in request.metadata:
                    if operator != "not_equals":
                        return False
                    continue

                target_value = request.metadata[field]

                if operator == "equals":
                    if target_value != value:
                        return False
                elif operator == "contains":
                    if value not in str(target_value):
                        return False

        return True

    async def _assess_risk(
        self,
        request: GatekeeperCheckRequest,
        triggered_rules: list[dict[str, Any]]
    ) -> RiskAssessment:
        """
        Assess risk for an action.

        Risk factors:
        - Triggered rules (severity-based)
        - Action type (some actions are inherently risky)
        - Actor (non-system actors have higher risk)
        - Target data (size, sensitivity)

        Args:
            request: Validation request
            triggered_rules: Rules that were triggered

        Returns:
            Risk assessment result
        """
        risk_factors = []
        risk_score = 0.0

        # Risk from triggered rules
        for rule in triggered_rules:
            severity = rule.get("severity", "low")
            if severity == "critical":
                risk_score += 0.3
            elif severity == "high":
                risk_score += 0.2
            elif severity == "medium":
                risk_score += 0.1
            else:  # low
                risk_score += 0.05

            risk_factors.append({
                "type": "governance_rule",
                "description": f"Rule '{rule['name']}' triggered",
                "severity": severity
            })

        # Risk from action type
        risky_actions = ["delete", "deploy", "execute", "overwrite", "destroy"]
        if request.action_type in risky_actions:
            risk_score += 0.15
            risk_factors.append({
                "type": "action_type",
                "description": f"High-risk action type: {request.action_type}",
                "severity": "medium"
            })

        # Risk from actor
        if "system" not in request.actor.lower():
            risk_score += 0.05
            risk_factors.append({
                "type": "actor",
                "description": "Non-system actor",
                "severity": "low"
            })

        # Risk from scope
        if "production" in request.scope.lower():
            risk_score += 0.1
            risk_factors.append({
                "type": "scope",
                "description": "Production scope action",
                "severity": "medium"
            })

        # Risk from target data size
        if request.target_data:
            data_size = len(str(request.target_data))
            if data_size > LARGE_PAYLOAD_THRESHOLD:  # Large payload
                risk_score += 0.05
                risk_factors.append({
                    "type": "data_size",
                    "description": f"Large payload: {data_size} bytes",
                    "severity": "low"
                })

        # Normalize risk score
        risk_score = min(risk_score, 1.0)

        # Determine severity level based on constants
        if risk_score >= RISK_SCORE_CRITICAL:
            severity = Severity.CRITICAL
        elif risk_score >= RISK_SCORE_HIGH:
            severity = Severity.HIGH
        elif risk_score >= RISK_SCORE_MEDIUM:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        # Generate recommendations
        recommendations = []
        if risk_score >= 0.5:
            recommendations.append("Review action before proceeding")
        if risk_score >= 0.7:
            recommendations.append("Consider alternative approaches")
        if any(rf["type"] == "governance_rule" for rf in risk_factors):
            recommendations.append("Ensure all governance requirements are met")
        if risk_score >= 0.3 and "production" in request.scope.lower():
            recommendations.append("Test in staging environment first")

        return RiskAssessment(
            risk_score=risk_score,
            risk_factors=risk_factors,
            severity=severity,
            recommendations=recommendations
        )

    async def _generate_alternatives(
        self,
        request: GatekeeperCheckRequest,
        triggered_rules: list[dict[str, Any]]
    ) -> list[str]:
        """
        Generate alternative approaches for blocked/review actions.

        Args:
            request: Original validation request
            triggered_rules: Rules that were triggered

        Returns:
            List of alternative approaches
        """
        alternatives = []

        # Based on action type
        action_alternatives = {
            "delete": [
                "Consider archiving instead of deleting",
                "Use soft-delete with retention period",
                "Export data before deletion"
            ],
            "deploy": [
                "Request approval from authorized personnel",
                "Deploy to staging environment first",
                "Create rollback plan before deploy"
            ],
            "memory_update": [
                "Create a new memory instead of updating",
                "Use memory evolution patch system"
            ],
            "overwrite": [
                "Create a new version instead of overwriting",
                "Review existing content first"
            ],
            "merge": [
                "Review merge conflicts carefully",
                "Request manual review before merge"
            ],
            "execute": [
                "Run in sandboxed environment",
                "Review code before execution",
                "Request approval for execution"
            ]
        }

        if request.action_type in action_alternatives:
            alternatives.extend(action_alternatives[request.action_type])

        # Based on scope
        if "production" in request.scope.lower():
            alternatives.extend([
                "Perform action in development environment first",
                "Request additional testing and validation",
                "Schedule during maintenance window"
            ])

        # Based on triggered rules
        for rule in triggered_rules:
            if "approval" in rule["name"].lower():
                alternatives.append(f"Obtain approval as per '{rule['name']}' rule")
            if "review" in rule["name"].lower():
                alternatives.append(f"Complete review as per '{rule['name']}' rule")
            if "backup" in rule["name"].lower():
                alternatives.append(f"Create backup as per '{rule['name']}' rule")

        # Deduplicate while preserving order
        seen = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt not in seen:
                seen.add(alt)
                unique_alternatives.append(alt)

        return unique_alternatives

    def _generate_reason(
        self,
        triggered_rules: list[dict[str, Any]],
        severity: Severity
    ) -> str:
        """
        Generate reason for governance decision.

        Args:
            triggered_rules: Rules that were triggered
            severity: Highest severity level

        Returns:
            Human-readable reason
        """
        if not triggered_rules:
            return "Action complies with all governance rules"

        count = len(triggered_rules)
        if severity == Severity.CRITICAL:
            return f"CRITICAL: {count} critical governance rule(s) violated"
        elif severity == Severity.HIGH:
            return f"HIGH: {count} high-severity governance rule(s) triggered"
        elif severity == Severity.MEDIUM:
            return f"MEDIUM: {count} governance rule(s) triggered - review recommended"
        else:
            return f"LOW: {count} governance rule(s) triggered - proceed with caution"

    def _severity_compare(self, s1: Severity, s2: Severity) -> int:
        """Compare two severity levels."""
        order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(s1) - order.index(s2)

    def _action_compare(self, a1: Action, a2: Action) -> int:
        """Compare two actions (more restrictive > less restrictive)."""
        restrictiveness = {
            Action.ALLOW: 0,
            Action.WARN: 1,
            Action.REVIEW: 2,
            Action.ALTERNATIVE: 3,
            Action.BLOCK: 4
        }
        return restrictiveness[a1] - restrictiveness[a2]

    # Batch Operations

    async def bulk_enable_rules(self, rule_ids: list[UUID]) -> list[GovernanceRuleResponse]:
        """
        Enable multiple rules at once.

        Args:
            rule_ids: List of rule IDs to enable

        Returns:
            List of updated rules
        """
        updated = []
        for rule_id in rule_ids:
            update_data = GovernanceRuleUpdate(enabled=True)
            rule = await self.repo.update_rule(rule_id, update_data)
            if rule:
                updated.append(rule)
        return updated

    async def bulk_disable_rules(self, rule_ids: list[UUID]) -> list[GovernanceRuleResponse]:
        """
        Disable multiple rules at once.

        Args:
            rule_ids: List of rule IDs to disable

        Returns:
            List of updated rules
        """
        updated = []
        for rule_id in rule_ids:
            update_data = GovernanceRuleUpdate(enabled=False)
            rule = await self.repo.update_rule(rule_id, update_data)
            if rule:
                updated.append(rule)
        return updated

    # Rule Templates

    async def create_rule_from_template(
        self,
        template: str,
        params: dict[str, Any]
    ) -> GovernanceRuleResponse:
        """
        Create a rule from a predefined template.

        Available templates:
        - "no_deploy_without_snapshot": Block deploy without snapshot
        - "avoid_known_failures": Warn about known failures
        - "production_approval": Require approval for production
        - "data_retention": Enforce data retention policy
        - "access_control": Restrict access by role

        Args:
            template: Template name
            params: Template parameters

        Returns:
            Created rule
        """
        templates = {
            "no_deploy_without_snapshot": {
                "name": "no_deploy_without_snapshot",
                "description": "Kein Deploy ohne Snapshot",
                "condition": {
                    "action_type": "deploy",
                    "data_conditions": [
                        {"field": "has_snapshot", "operator": "equals", "value": False}
                    ]
                },
                "action": Action.BLOCK,
                "severity": Severity.HIGH
            },
            "avoid_known_failures": {
                "name": "avoid_known_failures",
                "description": "Bekannten Fehler nicht erneut ausführen",
                "condition": {
                    "action_type": "retry",
                    "data_conditions": [
                        {"field": "known_failure", "operator": "equals", "value": True}
                    ]
                },
                "action": Action.WARN,
                "severity": Severity.MEDIUM
            },
            "production_approval": {
                "name": "production_approval",
                "description": "Require approval for production changes",
                "condition": {
                    "scope_pattern": ".*production.*",
                    "action_type": "deploy"
                },
                "action": Action.REVIEW,
                "severity": Severity.HIGH
            },
            "data_retention": {
                "name": "data_retention",
                "description": "Enforce minimum data retention period",
                "condition": {
                    "action_type": "delete",
                    "data_conditions": [
                        {"field": "retention_days", "operator": "less_than", "value": 90}
                    ]
                },
                "action": Action.BLOCK,
                "severity": Severity.CRITICAL
            },
            "access_control": {
                "name": "access_control",
                "description": "Restrict sensitive operations to authorized roles",
                "condition": {
                    "action_type": "delete",
                    "data_conditions": [
                        {"field": "actor_role", "operator": "not_equals", "value": "admin"}
                    ]
                },
                "action": Action.BLOCK,
                "severity": Severity.CRITICAL
            }
        }

        if template not in templates:
            raise ValueError(f"Unknown template: {template}")

        template_data = templates[template]

        # Override with params
        name = params.get("name", template_data["name"])
        scope = params.get("scope")
        enabled = params.get("enabled", True)

        rule_data = GovernanceRuleCreate(
            name=name,
            description=template_data["description"],
            condition=template_data["condition"],
            action=template_data["action"],
            severity=template_data["severity"],
            scope=scope,
            enabled=enabled
        )

        return await self.create_rule(rule_data)

    # Rule Chaining

    async def evaluate_rule_chain(
        self,
        request: GatekeeperCheckRequest,
        chain_name: str | None = None
    ) -> tuple[GatekeeperCheckResponse, list[dict]]:
        """
        Evaluate rules in a chain (sequence evaluation).

        Rules are evaluated in order, and later rules can see the results
        of earlier rule evaluations. This enables complex logic like:
        "If rule A triggers, also evaluate rule B"

        Args:
            request: Validation request
            chain_name: Optional name of rule chain to use

        Returns:
            Tuple of (final_response, evaluation_chain)
        """
        evaluation_chain = []

        # Get rules to evaluate
        if chain_name:
            # Get rules for specific chain
            rules = await self.repo.get_rules_by_chain(chain_name)
        else:
            # Get all applicable rules, ordered by priority
            rules = await self.repo.get_applicable_rules(
                action_type=request.action_type,
                scope=request.scope,
                enabled_only=True
            )

        # Evaluate each rule in sequence
        current_request = request
        all_triggered_rules = []
        final_response = None

        for i, rule in enumerate(rules):
            # Check if this rule should be evaluated based on previous results
            if i > 0:
                # Check if previous rules affect this rule
                should_evaluate = await self._should_evaluate_next_rule(
                    rule, evaluation_chain
                )
                if not should_evaluate:
                    continue

            # Evaluate this rule
            rule_triggered = self._evaluate_condition(rule.condition, current_request)

            evaluation_step = {
                "step": i + 1,
                "rule_id": str(rule.rule_id),
                "rule_name": rule.name,
                "triggered": rule_triggered,
                "action": rule.action if rule_triggered else None
            }
            evaluation_chain.append(evaluation_step)

            if rule_triggered:
                all_triggered_rules.append({
                    "rule_id": str(rule.rule_id),
                    "name": rule.name,
                    "description": rule.description,
                    "action": rule.action,
                    "severity": rule.severity
                })

                # Update request based on rule action (for next rules)
                current_request = await self._apply_rule_effects(
                    current_request, rule, evaluation_chain
                )

        # Generate final response
        if all_triggered_rules:
            highest_severity = max(
                [Severity(r["severity"]) for r in all_triggered_rules],
                key=lambda s: [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL].index(s)
            )
        else:
            highest_severity = Severity.LOW

        # Calculate risk assessment
        risk_assessment = await self._assess_risk(request, all_triggered_rules)

        # Determine final action
        recommended_action = self._determine_action_from_chain(evaluation_chain)
        allowed = recommended_action in [Action.ALLOW, Action.WARN]

        # Generate warnings and alternatives
        warnings = []
        alternatives = []

        if recommended_action == Action.WARN:
            warnings.append(f"Action triggers {len(all_triggered_rules)} governance rule(s)")
        elif recommended_action == Action.REVIEW:
            warnings.append("Action requires review before proceeding")
        elif recommended_action == Action.BLOCK:
            warnings.append("Action is blocked by governance rules")
            alternatives = await self._generate_alternatives(request, all_triggered_rules)
        elif recommended_action == Action.ALTERNATIVE:
            warnings.append("Alternative approach recommended")
            alternatives = await self._generate_alternatives(request, all_triggered_rules)

        final_response = GatekeeperCheckResponse(
            allowed=allowed,
            action=recommended_action.value,
            reason=self._generate_reason(all_triggered_rules, highest_severity),
            triggered_rules=all_triggered_rules,
            risk_score=risk_assessment.risk_score,
            alternatives=alternatives,
            warnings=warnings
        )

        logger.info(
            f"Rule chain evaluation: {len(evaluation_chain)} steps, "
            f"{len(all_triggered_rules)} triggered, action={recommended_action.value}"
        )

        return final_response, evaluation_chain

    async def _should_evaluate_next_rule(
        self,
        rule: GovernanceRuleResponse,
        evaluation_chain: list[dict]
    ) -> bool:
        """
        Determine if next rule should be evaluated based on previous results.

        Args:
            rule: Rule to potentially evaluate
            evaluation_chain: Previous evaluation results

        Returns:
            True if rule should be evaluated
        """
        # Check rule conditions for chain evaluation
        if not rule.condition:
            return True

        # Check if rule has "only_if_previous_triggered" condition
        if "only_if_previous_triggered" in rule.condition:
            if evaluation_chain:
                last_triggered = evaluation_chain[-1].get("triggered", False)
                return last_triggered
            return False

        # Check if rule has "only_if_previous_allowed" condition
        if "only_if_previous_allowed" in rule.condition:
            if evaluation_chain:
                last_action = evaluation_chain[-1].get("action")
                return last_action in ["allow", "warn"]
            return True

        # Default: evaluate the rule
        return True

    async def _apply_rule_effects(
        self,
        request: GatekeeperCheckRequest,
        rule: GovernanceRuleResponse,
        evaluation_chain: list[dict]
    ) -> GatekeeperCheckRequest:
        """
        Apply effects of a triggered rule to the request for subsequent rules.

        Args:
            request: Current request
            rule: Rule that was triggered
            evaluation_chain: Evaluation history

        Returns:
            Modified request for next evaluation
        """
        # Create a copy of the request
        modified_request = GatekeeperCheckRequest(
            action_type=request.action_type,
            actor=request.actor,
            scope=request.scope,
            target_data=request.target_data.copy(),
            metadata=request.metadata.copy()
        )

        # Apply rule effects based on action
        if rule.action == "review":
            # Add pending review flag
            modified_request.target_data["pending_review"] = True
            modified_request.metadata["review_required_by"] = rule.name

        elif rule.action == "alternative":
            # Add alternative suggestion flag
            modified_request.target_data["alternative_suggested"] = True
            modified_request.metadata["alternative_source"] = rule.name

        elif rule.action == "block":
            # Add blocked flag
            modified_request.target_data["blocked"] = True
            modified_request.metadata["blocked_by"] = rule.name

        return modified_request

    def _determine_action_from_chain(self, evaluation_chain: list[dict]) -> Action:
        """
        Determine final action from evaluation chain.

        Args:
            evaluation_chain: Rule evaluation results

        Returns:
            Final recommended action
        """
        # Find the most restrictive action among triggered rules
        triggered_actions = [
            step["action"] for step in evaluation_chain
            if step.get("triggered") and step.get("action")
        ]

        if not triggered_actions:
            return Action.ALLOW

        # Order by restrictiveness
        restrictiveness = {
            Action.ALLOW: 0,
            Action.WARN: 1,
            Action.REVIEW: 2,
            Action.ALTERNATIVE: 3,
            Action.BLOCK: 4
        }

        # Return the most restrictive action
        most_restrictive = max(
            [Action(action) for action in triggered_actions],
            key=lambda a: restrictiveness.get(a, 0)
        )

        return most_restrictive

    # Batch Evaluation

    async def batch_evaluate_rules(
        self,
        requests: list[GatekeeperCheckRequest]
    ) -> list[tuple[GatekeeperCheckResponse, RiskAssessment]]:
        """
        Evaluate multiple requests in batch (efficient evaluation).

        Args:
            requests: List of validation requests

        Returns:
            List of (response, risk_assessment) tuples
        """
        results = []

        # Group requests by action_type and scope for efficient rule lookup
        grouped = defaultdict(list)
        for i, request in enumerate(requests):
            key = (request.action_type, request.scope)
            grouped[key].append((i, request))

        # Evaluate each group
        for key, group_requests in grouped.items():
            action_type, scope = key

            # Get applicable rules once per group
            rules = await self.repo.get_applicable_rules(
                action_type=action_type,
                scope=scope,
                enabled_only=True
            )

            # Evaluate each request in the group
            for idx, request in group_requests:
                response, risk = await self.evaluate_rules(request, rules)
                results.append((response, risk))

        # Sort results back to original order
        sorted_results = [None] * len(requests)
        for original_idx, result in enumerate(results):
            sorted_results[original_idx] = result

        logger.info(f"Batch evaluation: {len(requests)} requests processed")

        return sorted_results

    # Action Execution Tracking

    async def track_action_execution(
        self,
        request: GatekeeperCheckRequest,
        response: GatekeeperCheckResponse,
        actually_executed: bool,
        execution_result: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Track action execution for analytics and governance.

        Args:
            request: Original validation request
            response: Governance response
            actually_executed: Whether action was actually executed
            execution_result: Result of execution (if any)

        Returns:
            Tracking record
        """
        tracking_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": request.action_type,
            "actor": request.actor,
            "scope": request.scope,
            "governance_decision": {
                "allowed": response.allowed,
                "recommended_action": response.action,
                "risk_score": response.risk_score,
                "triggered_rules_count": len(response.triggered_rules)
            },
            "execution": {
                "executed": actually_executed,
                "result": execution_result
            }
        }

        # Log the tracking record
        logger.info(
            f"Action execution tracking: {request.action_type} by {request.actor}, "
            f"allowed={response.allowed}, executed={actually_executed}"
        )

        # TODO: Store in database for analytics
        # await self.repo.store_execution_tracking(tracking_record)

        return tracking_record

    async def get_execution_analytics(
        self,
        action_type: str | None = None,
        actor: str | None = None,
        scope: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        Get execution analytics for governance insights.

        Args:
            action_type: Filter by action type
            actor: Filter by actor
            scope: Filter by scope
            from_date: Start date
            to_date: End date

        Returns:
            Analytics data
        """
        # TODO: Implement analytics query from tracking data
        analytics = {
            "total_actions": 0,
            "allowed_actions": 0,
            "blocked_actions": 0,
            "high_risk_actions": 0,
            "most_triggered_rules": [],
            "action_types_breakdown": {},
            "compliance_rate": 0.0
        }

        logger.info(
            f"Execution analytics query: action_type={action_type}, "
            f"actor={actor}, scope={scope}"
        )

        return analytics

    # Rule Performance Metrics

    async def get_rule_performance_metrics(
        self,
        rule_id: UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        Get performance metrics for a specific rule.

        Args:
            rule_id: Rule ID
            from_date: Start date
            to_date: End date

        Returns:
            Rule performance metrics
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        # TODO: Calculate from execution tracking data
        metrics = {
            "rule_id": str(rule_id),
            "rule_name": rule.name,
            "evaluation_count": 0,
            "trigger_count": 0,
            "trigger_rate": 0.0,
            "block_count": 0,
            "warn_count": 0,
            "review_count": 0,
            "average_risk_score": 0.0,
            "false_positive_rate": 0.0
        }

        logger.info(f"Rule performance metrics: {rule.name}")

        return metrics
