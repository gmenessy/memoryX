"""
Governance Repository - Data Access Layer for Governance Rules
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import GovernanceRuleDB, GovernanceRuleCreate, GovernanceRuleUpdate, GovernanceRuleResponse


class GovernanceRepository:
    """
    Repository for Governance Rule operations.
    Manages executable governance rules for memory operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_rule(self, rule_data: GovernanceRuleCreate) -> GovernanceRuleResponse:
        """
        Create a new governance rule.

        Args:
            rule_data: Rule creation data

        Returns:
            Created rule response
        """
        rule_db = GovernanceRuleDB(
            name=rule_data.name,
            description=rule_data.description,
            condition=rule_data.condition,
            action=rule_data.action.value,
            severity=rule_data.severity.value,
            scope=rule_data.scope,
            enabled=rule_data.enabled
        )

        self.session.add(rule_db)
        await self.session.flush()
        await self.session.refresh(rule_db)

        return GovernanceRuleResponse(
            rule_id=rule_db.rule_id,
            name=rule_db.name,
            description=rule_db.description,
            condition=rule_db.condition,
            action=rule_db.action,
            severity=rule_db.severity,
            scope=rule_db.scope,
            enabled=rule_db.enabled,
            created_at=rule_db.created_at,
            updated_at=rule_db.updated_at
        )

    async def get_rule(self, rule_id: UUID) -> GovernanceRuleResponse | None:
        """
        Get rule by ID.

        Args:
            rule_id: Rule UUID

        Returns:
            Rule response or None if not found
        """
        result = await self.session.execute(
            select(GovernanceRuleDB).where(GovernanceRuleDB.rule_id == rule_id)
        )
        rule_db = result.scalar_one_or_none()

        if not rule_db:
            return None

        return GovernanceRuleResponse(
            rule_id=rule_db.rule_id,
            name=rule_db.name,
            description=rule_db.description,
            condition=rule_db.condition,
            action=rule_db.action,
            severity=rule_db.severity,
            scope=rule_db.scope,
            enabled=rule_db.enabled,
            created_at=rule_db.created_at,
            updated_at=rule_db.updated_at
        )

    async def get_rule_by_name(self, name: str) -> GovernanceRuleResponse | None:
        """
        Get rule by name.

        Args:
            name: Rule name

        Returns:
            Rule response or None if not found
        """
        result = await self.session.execute(
            select(GovernanceRuleDB).where(GovernanceRuleDB.name == name)
        )
        rule_db = result.scalar_one_or_none()

        if not rule_db:
            return None

        return GovernanceRuleResponse(
            rule_id=rule_db.rule_id,
            name=rule_db.name,
            description=rule_db.description,
            condition=rule_db.condition,
            action=rule_db.action,
            severity=rule_db.severity,
            scope=rule_db.scope,
            enabled=rule_db.enabled,
            created_at=rule_db.created_at,
            updated_at=rule_db.updated_at
        )

    async def update_rule(self, rule_id: UUID, update_data: GovernanceRuleUpdate) -> GovernanceRuleResponse | None:
        """
        Update a governance rule.

        Args:
            rule_id: Rule UUID
            update_data: Update data

        Returns:
            Updated rule response or None if not found
        """
        result = await self.session.execute(
            select(GovernanceRuleDB).where(GovernanceRuleDB.rule_id == rule_id)
        )
        rule_db = result.scalar_one_or_none()

        if not rule_db:
            return None

        # Update fields
        if update_data.description is not None:
            rule_db.description = update_data.description
        if update_data.condition is not None:
            rule_db.condition = update_data.condition
        if update_data.action is not None:
            rule_db.action = update_data.action.value
        if update_data.severity is not None:
            rule_db.severity = update_data.severity.value
        if update_data.scope is not None:
            rule_db.scope = update_data.scope
        if update_data.enabled is not None:
            rule_db.enabled = update_data.enabled

        rule_db.updated_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(rule_db)

        return GovernanceRuleResponse(
            rule_id=rule_db.rule_id,
            name=rule_db.name,
            description=rule_db.description,
            condition=rule_db.condition,
            action=rule_db.action,
            severity=rule_db.severity,
            scope=rule_db.scope,
            enabled=rule_db.enabled,
            created_at=rule_db.created_at,
            updated_at=rule_db.updated_at
        )

    async def list_rules(
        self,
        enabled_only: bool = True,
        scope: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GovernanceRuleResponse]:
        """
        List governance rules with optional filtering.

        Args:
            enabled_only: Only return enabled rules
            scope: Filter by scope
            severity: Filter by severity
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of rules
        """
        query = select(GovernanceRuleDB)

        # Apply filters
        conditions = []
        if enabled_only:
            conditions.append(GovernanceRuleDB.enabled == True)
        if scope:
            conditions.append(GovernanceRuleDB.scope == scope)
        if severity:
            conditions.append(GovernanceRuleDB.severity == severity)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by severity (critical first) then name
        query = query.order_by(
            GovernanceRuleDB.severity.desc(),
            GovernanceRuleDB.name.asc()
        )

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        rules = result.scalars().all()

        return [
            GovernanceRuleResponse(
                rule_id=rule.rule_id,
                name=rule.name,
                description=rule.description,
                condition=rule.condition,
                action=rule.action,
                severity=rule.severity,
                scope=rule.scope,
                enabled=rule.enabled,
                created_at=rule.created_at,
                updated_at=rule.updated_at
            )
            for rule in rules
        ]

    async def delete_rule(self, rule_id: UUID) -> bool:
        """
        Delete a governance rule.

        Args:
            rule_id: Rule UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            select(GovernanceRuleDB).where(GovernanceRuleDB.rule_id == rule_id)
        )
        rule_db = result.scalar_one_or_none()

        if not rule_db:
            return False

        await self.session.delete(rule_db)
        await self.session.flush()

        return True

    async def count_rules(
        self,
        enabled_only: bool = True,
        scope: str | None = None
    ) -> int:
        """
        Count rules matching filters.

        Args:
            enabled_only: Only count enabled rules
            scope: Filter by scope

        Returns:
            Number of matching rules
        """
        from sqlalchemy import func

        query = select(func.count(GovernanceRuleDB.rule_id))

        conditions = []
        if enabled_only:
            conditions.append(GovernanceRuleDB.enabled == True)
        if scope:
            conditions.append(GovernanceRuleDB.scope == scope)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_applicable_rules(
        self,
        action_type: str,
        scope: str,
        enabled_only: bool = True
    ) -> list[GovernanceRuleResponse]:
        """
        Get rules applicable to a specific action and scope.

        Args:
            action_type: Type of action
            scope: Action scope
            enabled_only: Only return enabled rules

        Returns:
            List of applicable rules
        """
        # Get all enabled rules for the scope (or global rules)
        query = select(GovernanceRuleDB)

        conditions = [
            or_(
                GovernanceRuleDB.scope == scope,
                GovernanceRuleDB.scope == "global",
                GovernanceRuleDB.scope.is_(None)
            )
        ]

        if enabled_only:
            conditions.append(GovernanceRuleDB.enabled == True)

        query = query.where(and_(*conditions))
        query = query.order_by(GovernanceRuleDB.severity.desc())

        result = await self.session.execute(query)
        rules = result.scalars().all()

        return [
            GovernanceRuleResponse(
                rule_id=rule.rule_id,
                name=rule.name,
                description=rule.description,
                condition=rule.condition,
                action=rule.action,
                severity=rule.severity,
                scope=rule.scope,
                enabled=rule.enabled,
                created_at=rule.created_at,
                updated_at=rule.updated_at
            )
            for rule in rules
        ]