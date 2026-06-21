"""
Dream Repository - Data Access Layer for Dream Engine

Manages database operations for:
- Daydream Jobs (Event → Memory)
- Nightdream Jobs (Merge, Compress, Deduplicate)
- Deepdream Jobs (Pattern Discovery, Policy Discovery)
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dream import (
    DaydreamJobDB,
    NightdreamJobDB,
    DeepdreamJobDB,
    DaydreamJobResponse,
    NightdreamJobResponse,
    DeepdreamJobResponse,
    DreamType,
    DreamStatus,
)


class DreamRepository:
    """
    Repository for Dream Engine operations.
    Manages all database interactions for dream jobs.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # Daydream Operations

    async def create_daydream_job(self, job: DaydreamJobDB) -> DaydreamJobDB:
        """Create a new daydream job."""
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_daydream_job(self, job_id: UUID) -> DaydreamJobDB | None:
        """Get daydream job by ID."""
        result = await self.session.execute(
            select(DaydreamJobDB).where(DaydreamJobDB.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_daydream_jobs(
        self,
        status: str | None = None,
        transformation_type: str | None = None,
        priority_min: float | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[DaydreamJobDB]:
        """List daydream jobs with optional filters."""
        query = select(DaydreamJobDB)

        conditions = []
        if status:
            conditions.append(DaydreamJobDB.status == status)
        if transformation_type:
            conditions.append(DaydreamJobDB.transformation_type == transformation_type)
        if priority_min is not None:
            conditions.append(DaydreamJobDB.priority >= priority_min)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(
            DaydreamJobDB.priority.desc(),
            DaydreamJobDB.created_at.asc()
        ).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_daydream_job(self, job: DaydreamJobDB) -> DaydreamJobDB:
        """Update daydream job."""
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def delete_daydream_job(self, job_id: UUID) -> bool:
        """Delete daydream job by ID."""
        job = await self.get_daydream_job(job_id)
        if job:
            await self.session.delete(job)
            await self.session.commit()
            return True
        return False

    async def count_daydream_jobs(
        self,
        status: str | None = None
    ) -> int:
        """Count daydream jobs with optional filters."""
        from sqlalchemy import func

        query = select(func.count(DaydreamJobDB.job_id))

        if status:
            query = query.where(DaydreamJobDB.status == status)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_pending_daydream_jobs(self, limit: int = 50) -> list[DaydreamJobDB]:
        """Get pending daydream jobs ordered by priority."""
        result = await self.session.execute(
            select(DaydreamJobDB).where(DaydreamJobDB.status == DreamStatus.PENDING.value)
            .order_by(DaydreamJobDB.priority.desc(), DaydreamJobDB.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # Nightdream Operations

    async def create_nightdream_job(self, job: NightdreamJobDB) -> NightdreamJobDB:
        """Create a new nightdream job."""
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_nightdream_job(self, job_id: UUID) -> NightdreamJobDB | None:
        """Get nightdream job by ID."""
        result = await self.session.execute(
            select(NightdreamJobDB).where(NightdreamJobDB.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_nightdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None,
        scope: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[NightdreamJobDB]:
        """List nightdream jobs with optional filters."""
        query = select(NightdreamJobDB)

        conditions = []
        if status:
            conditions.append(NightdreamJobDB.status == status)
        if operation:
            conditions.append(NightdreamJobDB.operation == operation)
        if scope:
            conditions.append(NightdreamJobDB.scope == scope)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(NightdreamJobDB.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_nightdream_job(self, job: NightdreamJobDB) -> NightdreamJobDB:
        """Update nightdream job."""
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def delete_nightdream_job(self, job_id: UUID) -> bool:
        """Delete nightdream job by ID."""
        job = await self.get_nightdream_job(job_id)
        if job:
            await self.session.delete(job)
            await self.session.commit()
            return True
        return False

    async def count_nightdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None
    ) -> int:
        """Count nightdream jobs with optional filters."""
        from sqlalchemy import func

        query = select(func.count(NightdreamJobDB.job_id))

        conditions = []
        if status:
            conditions.append(NightdreamJobDB.status == status)
        if operation:
            conditions.append(NightdreamJobDB.operation == operation)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_scheduled_nightdream_jobs(self, limit: int = 50) -> list[NightdreamJobDB]:
        """Get scheduled nightdream jobs that are due."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(NightdreamJobDB).where(
                and_(
                    NightdreamJobDB.status == DreamStatus.PENDING.value,
                    or_(
                        NightdreamJobDB.scheduled_for <= now,
                        NightdreamJobDB.scheduled_for.is_(None)
                    )
                )
            )
            .order_by(NightdreamJobDB.scheduled_for.asc().nulls_first(), NightdreamJobDB.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # Deepdream Operations

    async def create_deepdream_job(self, job: DeepdreamJobDB) -> DeepdreamJobDB:
        """Create a new deepdream job."""
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_deepdream_job(self, job_id: UUID) -> DeepdreamJobDB | None:
        """Get deepdream job by ID."""
        result = await self.session.execute(
            select(DeepdreamJobDB).where(DeepdreamJobDB.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_deepdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None,
        scope: str | None = None,
        analysis_depth: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[DeepdreamJobDB]:
        """List deepdream jobs with optional filters."""
        query = select(DeepdreamJobDB)

        conditions = []
        if status:
            conditions.append(DeepdreamJobDB.status == status)
        if operation:
            conditions.append(DeepdreamJobDB.operation == operation)
        if scope:
            conditions.append(DeepdreamJobDB.scope == scope)
        if analysis_depth:
            conditions.append(DeepdreamJobDB.analysis_depth == analysis_depth)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(DeepdreamJobDB.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_deepdream_job(self, job: DeepdreamJobDB) -> DeepdreamJobDB:
        """Update deepdream job."""
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def delete_deepdream_job(self, job_id: UUID) -> bool:
        """Delete deepdream job by ID."""
        job = await self.get_deepdream_job(job_id)
        if job:
            await self.session.delete(job)
            await self.session.commit()
            return True
        return False

    async def count_deepdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None
    ) -> int:
        """Count deepdream jobs with optional filters."""
        from sqlalchemy import func

        query = select(func.count(DeepdreamJobDB.job_id))

        conditions = []
        if status:
            conditions.append(DeepdreamJobDB.status == status)
        if operation:
            conditions.append(DeepdreamJobDB.operation == operation)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_pending_deepdream_jobs(self, limit: int = 50) -> list[DeepdreamJobDB]:
        """Get pending deepdream jobs."""
        result = await self.session.execute(
            select(DeepdreamJobDB).where(DeepdreamJobDB.status == DreamStatus.PENDING.value)
            .order_by(DeepdreamJobDB.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # Statistics

    async def get_dream_statistics(self) -> dict[str, Any]:
        """Get overall dream engine statistics."""
        from sqlalchemy import func

        # Daydream stats
        daydream_result = await self.session.execute(
            select(
                func.count(DaydreamJobDB.job_id).label('total'),
                func.sum(func.case((DaydreamJobDB.status == DreamStatus.PENDING.value, 1), else_=0)).label('pending'),
                func.sum(func.case((DaydreamJobDB.status == DreamStatus.RUNNING.value, 1), else_=0)).label('running'),
                func.sum(func.case((DaydreamJobDB.status == DreamStatus.COMPLETED.value, 1), else_=0)).label('completed'),
                func.sum(func.case((DaydreamJobDB.status == DreamStatus.FAILED.value, 1), else_=0)).label('failed')
            )
        )
        dd_stats = daydream_result.one()

        # Nightdream stats
        nightdream_result = await self.session.execute(
            select(
                func.count(NightdreamJobDB.job_id).label('total'),
                func.sum(func.case((NightdreamJobDB.status == DreamStatus.PENDING.value, 1), else_=0)).label('pending'),
                func.sum(func.case((NightdreamJobDB.status == DreamStatus.RUNNING.value, 1), else_=0)).label('running'),
                func.sum(func.case((NightdreamJobDB.status == DreamStatus.COMPLETED.value, 1), else_=0)).label('completed'),
                func.sum(func.case((NightdreamJobDB.status == DreamStatus.FAILED.value, 1), else_=0)).label('failed')
            )
        )
        nd_stats = nightdream_result.one()

        # Deepdream stats
        deepdream_result = await self.session.execute(
            select(
                func.count(DeepdreamJobDB.job_id).label('total'),
                func.sum(func.case((DeepdreamJobDB.status == DreamStatus.PENDING.value, 1), else_=0)).label('pending'),
                func.sum(func.case((DeepdreamJobDB.status == DreamStatus.RUNNING.value, 1), else_=0)).label('running'),
                func.sum(func.case((DeepdreamJobDB.status == DreamStatus.COMPLETED.value, 1), else_=0)).label('completed'),
                func.sum(func.case((DeepdreamJobDB.status == DreamStatus.FAILED.value, 1), else_=0)).label('failed')
            )
        )
        dp_stats = deepdream_result.one()

        return {
            "daydream": {
                "total": dd_stats.total or 0,
                "pending": dd_stats.pending or 0,
                "running": dd_stats.running or 0,
                "completed": dd_stats.completed or 0,
                "failed": dd_stats.failed or 0
            },
            "nightdream": {
                "total": nd_stats.total or 0,
                "pending": nd_stats.pending or 0,
                "running": nd_stats.running or 0,
                "completed": nd_stats.completed or 0,
                "failed": nd_stats.failed or 0
            },
            "deepdream": {
                "total": dp_stats.total or 0,
                "pending": dp_stats.pending or 0,
                "running": dp_stats.running or 0,
                "completed": dp_stats.completed or 0,
                "failed": dp_stats.failed or 0
            }
        }
