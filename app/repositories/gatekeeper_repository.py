"""
Gatekeeper Repository - Data Access Layer

Handles all database operations for:
- Policies
- Risk Assessments
- Gatekeeper Checks
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gatekeeper import (
    PolicyDB,
    RiskAssessmentDB,
    GatekeeperCheckDB,
    PolicyResponse,
    RiskAssessmentResponse,
    GatekeeperCheckResponse,
)


class GatekeeperRepository:
    """
    Repository for Gatekeeper operations.
    Handles all database interactions for policies, risks, and checks.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # Policy Operations

    async def create_policy(self, policy: PolicyDB) -> PolicyDB:
        """Create a new policy."""
        self.session.add(policy)
        await self.session.commit()
        await self.session.refresh(policy)
        return policy

    async def get_policy(self, policy_id: UUID) -> PolicyDB | None:
        """Get policy by ID."""
        result = await self.session.execute(
            select(PolicyDB).where(PolicyDB.policy_id == policy_id)
        )
        return result.scalar_one_or_none()

    async def get_policy_by_name(self, name: str) -> PolicyDB | None:
        """Get policy by name."""
        result = await self.session.execute(
            select(PolicyDB).where(PolicyDB.name == name)
        )
        return result.scalar_one_or_none()

    async def list_policies(
        self,
        scope: str | None = None,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> list[PolicyDB]:
        """List policies with optional filters."""
        query = select(PolicyDB)

        conditions = []
        if scope:
            conditions.append(PolicyDB.scope == scope)
        if active_only:
            conditions.append(PolicyDB.active == True)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(PolicyDB.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_policy(self, policy: PolicyDB) -> PolicyDB:
        """Update existing policy."""
        policy.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(policy)
        return policy

    async def delete_policy(self, policy_id: UUID) -> bool:
        """Delete policy by ID."""
        policy = await self.get_policy(policy_id)
        if policy:
            await self.session.delete(policy)
            await self.session.commit()
            return True
        return False

    async def count_policies(
        self,
        scope: str | None = None,
        active_only: bool = False
    ) -> int:
        """Count policies with optional filters."""
        from sqlalchemy import func

        query = select(func.count(PolicyDB.policy_id))

        conditions = []
        if scope:
            conditions.append(PolicyDB.scope == scope)
        if active_only:
            conditions.append(PolicyDB.active == True)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar()

    async def get_active_policies_for_scope(self, scope: str) -> list[PolicyDB]:
        """Get all active policies for a given scope."""
        result = await self.session.execute(
            select(PolicyDB).where(
                and_(
                    PolicyDB.scope == scope,
                    PolicyDB.active == True
                )
            )
        )
        return list(result.scalars().all())

    async def get_policies_by_action(self, action: str) -> list[PolicyDB]:
        """Get all active policies that trigger on a specific action."""
        result = await self.session.execute(
            select(PolicyDB).where(
                and_(
                    PolicyDB.active == True,
                    PolicyDB.condition["action"].astext == action
                )
            )
        )
        return list(result.scalars().all())

    # Risk Assessment Operations

    async def create_risk_assessment(self, risk: RiskAssessmentDB) -> RiskAssessmentDB:
        """Create a new risk assessment."""
        self.session.add(risk)
        await self.session.commit()
        await self.session.refresh(risk)
        return risk

    async def get_risk_assessment(self, assessment_id: UUID) -> RiskAssessmentDB | None:
        """Get risk assessment by ID."""
        result = await self.session.execute(
            select(RiskAssessmentDB).where(RiskAssessmentDB.assessment_id == assessment_id)
        )
        return result.scalar_one_or_none()

    async def list_risk_assessments(
        self,
        action_type: str | None = None,
        scope: str | None = None,
        risk_level: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[RiskAssessmentDB]:
        """List risk assessments with optional filters."""
        query = select(RiskAssessmentDB)

        conditions = []
        if action_type:
            conditions.append(RiskAssessmentDB.action_type == action_type)
        if scope:
            conditions.append(RiskAssessmentDB.scope == scope)
        if risk_level:
            conditions.append(RiskAssessmentDB.risk_level == risk_level)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(RiskAssessmentDB.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_risk_assessment(self, risk: RiskAssessmentDB) -> RiskAssessmentDB:
        """Update existing risk assessment."""
        await self.session.commit()
        await self.session.refresh(risk)
        return risk

    async def delete_risk_assessment(self, assessment_id: UUID) -> bool:
        """Delete risk assessment by ID."""
        risk = await self.get_risk_assessment(assessment_id)
        if risk:
            await self.session.delete(risk)
            await self.session.commit()
            return True
        return False

    async def count_risk_assessments(
        self,
        action_type: str | None = None,
        scope: str | None = None,
        risk_level: str | None = None
    ) -> int:
        """Count risk assessments with optional filters."""
        from sqlalchemy import func

        query = select(func.count(RiskAssessmentDB.assessment_id))

        conditions = []
        if action_type:
            conditions.append(RiskAssessmentDB.action_type == action_type)
        if scope:
            conditions.append(RiskAssessmentDB.scope == scope)
        if risk_level:
            conditions.append(RiskAssessmentDB.risk_level == risk_level)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar()

    async def get_risks_for_action(self, action_type: str, scope: str) -> list[RiskAssessmentDB]:
        """Get risk assessments for a specific action and scope."""
        result = await self.session.execute(
            select(RiskAssessmentDB).where(
                and_(
                    RiskAssessmentDB.action_type == action_type,
                    RiskAssessmentDB.scope == scope
                )
            )
        )
        return list(result.scalars().all())

    # Gatekeeper Check Operations

    async def create_check(self, check: GatekeeperCheckDB) -> GatekeeperCheckDB:
        """Create a new gatekeeper check record."""
        self.session.add(check)
        await self.session.commit()
        await self.session.refresh(check)
        return check

    async def get_check(self, check_id: UUID) -> GatekeeperCheckDB | None:
        """Get check by ID."""
        result = await self.session.execute(
            select(GatekeeperCheckDB).where(GatekeeperCheckDB.check_id == check_id)
        )
        return result.scalar_one_or_none()

    async def list_checks(
        self,
        action: str | None = None,
        result: str | None = None,
        scope: str | None = None,
        actor: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[GatekeeperCheckDB]:
        """List checks with optional filters."""
        query = select(GatekeeperCheckDB)

        conditions = []
        if action:
            conditions.append(GatekeeperCheckDB.action == action)
        if result:
            conditions.append(GatekeeperCheckDB.result == result)
        if scope:
            conditions.append(GatekeeperCheckDB.scope == scope)
        if actor:
            conditions.append(GatekeeperCheckDB.actor == actor)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(GatekeeperCheckDB.checked_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_checks(
        self,
        action: str | None = None,
        result: str | None = None,
        scope: str | None = None,
        actor: str | None = None
    ) -> int:
        """Count checks with optional filters."""
        from sqlalchemy import func

        query = select(func.count(GatekeeperCheckDB.check_id))

        conditions = []
        if action:
            conditions.append(GatekeeperCheckDB.action == action)
        if result:
            conditions.append(GatekeeperCheckDB.result == result)
        if scope:
            conditions.append(GatekeeperCheckDB.scope == scope)
        if actor:
            conditions.append(GatekeeperCheckDB.actor == actor)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar()

    async def get_checks_by_actor(self, actor: str, limit: int = 50) -> list[GatekeeperCheckDB]:
        """Get recent checks for a specific actor."""
        result = await self.session.execute(
            select(GatekeeperCheckDB).where(GatekeeperCheckDB.actor == actor)
            .order_by(GatekeeperCheckDB.checked_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_blocked_checks(self, scope: str, limit: int = 100) -> list[GatekeeperCheckDB]:
        """Get recently blocked actions for a scope."""
        result = await self.session.execute(
            select(GatekeeperCheckDB).where(
                and_(
                    GatekeeperCheckDB.scope == scope,
                    GatekeeperCheckDB.result == "block"
                )
            )
            .order_by(GatekeeperCheckDB.checked_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_check_statistics(
        self,
        scope: str | None = None,
        actor: str | None = None
    ) -> dict[str, Any]:
        """Get statistics about gatekeeper checks."""
        from sqlalchemy import func

        query = select(
            func.count(GatekeeperCheckDB.check_id).label('total'),
            func.sum(func.case((GatekeeperCheckDB.result == "allow", 1), else_=0)).label('allowed'),
            func.sum(func.case((GatekeeperCheckDB.result == "block", 1), else_=0)).label('blocked'),
            func.sum(func.case((GatekeeperCheckDB.result == "warn", 1), else_=0)).label('warnings'),
            func.sum(func.case((GatekeeperCheckDB.result == "review", 1), else_=0)).label('reviews'),
            func.avg(GatekeeperCheckDB.confidence).label('avg_confidence')
        )

        conditions = []
        if scope:
            conditions.append(GatekeeperCheckDB.scope == scope)
        if actor:
            conditions.append(GatekeeperCheckDB.actor == actor)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        row = result.one()

        return {
            "total": row.total or 0,
            "allowed": row.allowed or 0,
            "blocked": row.blocked or 0,
            "warnings": row.warnings or 0,
            "reviews": row.reviews or 0,
            "average_confidence": float(row.avg_confidence) if row.avg_confidence else 0.0
        }
