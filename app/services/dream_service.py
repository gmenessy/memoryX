"""
Dream Service - Business Logic Layer for Dream Engine

The Dream Engine provides asynchronous memory consolidation:
- Daydream: Event → Memory Transformation (running)
- Nightdream: Merge, Compress, Deduplicate (periodic)
- Deepdream: Pattern Discovery, Policy Discovery (strategic)
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dream import (
    DaydreamJobDB,
    NightdreamJobDB,
    DeepdreamJobDB,
    DaydreamJob,
    DaydreamJobCreate,
    NightdreamJob,
    NightdreamJobCreate,
    DeepdreamJob,
    DeepdreamJobCreate,
    DreamType,
    DreamStatus,
    TransformationType,
    NIGHTDREAM_OPERATIONS,
    DEEPDREAM_OPERATIONS,
)
from app.repositories.dream_repository import DreamRepository
from app.repositories.event_repository import EventRepository
from app.repositories.memory_repository import MemoryRepository


class DreamService:
    """
    Service for Dream Engine operations.
    Implements the business logic for memory consolidation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.dream_repo = DreamRepository(session)
        self.event_repo = EventRepository(session)
        self.memory_repo = MemoryRepository(session)

    # Daydream Operations (Event → Memory)

    async def create_daydream_job(self, job_create: DaydreamJobCreate) -> DaydreamJob:
        """
        Create a new daydream job for Event → Memory transformation.

        Daydream runs continuously, transforming events into memories.
        """
        # Validate source events exist
        for event_id in job_create.source_events:
            event = await self.event_repo.get_event(event_id)
            if not event:
                raise ValueError(f"Event {event_id} not found")

        job_db = DaydreamJobDB(
            dream_type=DreamType.DAYDREAM.value,
            status=DreamStatus.PENDING.value,
            transformation_type=job_create.transformation_type,
            source_events=job_create.source_events,
            processing_params=job_create.processing_params,
            priority=job_create.priority
        )

        created = await self.dream_repo.create_daydream_job(job_db)
        return DaydreamJob.model_validate(created)

    async def get_daydream_job(self, job_id: UUID) -> DaydreamJob | None:
        """Get daydream job by ID."""
        job = await self.dream_repo.get_daydream_job(job_id)
        return DaydreamJob.model_validate(job) if job else None

    async def list_daydream_jobs(
        self,
        status: str | None = None,
        transformation_type: str | None = None,
        priority_min: float | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[DaydreamJob]:
        """List daydream jobs."""
        jobs = await self.dream_repo.list_daydream_jobs(status, transformation_type, priority_min, limit, offset)
        return [DaydreamJob.model_validate(j) for j in jobs]

    async def process_daydream_job(self, job_id: UUID) -> DaydreamJob:
        """
        Process a daydream job - transform events into memory.

        This is the CORE function for Daydream.
        It performs Event → Memory transformation.
        """
        job = await self.dream_repo.get_daydream_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status != DreamStatus.PENDING.value:
            raise ValueError(f"Job {job_id} is not in pending status")

        # Update to running
        job.status = DreamStatus.RUNNING.value
        job.started_at = datetime.utcnow()
        await self.dream_repo.update_daydream_job(job)

        try:
            # Get source events
            events = []
            for event_id in job.source_events:
                event = await self.event_repo.get_event(event_id)
                if event:
                    events.append(event)

            if not events:
                raise ValueError("No valid events found")

            # Transform events to memory based on transformation type
            memory = await self._transform_events_to_memory(events, job)

            # Update job with result
            job.status = DreamStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()
            job.target_memory = memory.memory_id if memory else None
            job.result = {
                "memory_created": str(memory.memory_id) if memory else None,
                "events_processed": len(events),
                "transformation_type": job.transformation_type
            }

            return DaydreamJob.model_validate(await self.dream_repo.update_daydream_job(job))

        except Exception as e:
            job.status = DreamStatus.FAILED.value
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            await self.dream_repo.update_daydream_job(job)
            raise

    async def _transform_events_to_memory(
        self,
        events: list,
        job: DaydreamJobDB
    ) -> Any:
        """
        Transform events into memory based on transformation type.

        Transformation types:
        - direct: Direct event to memory (one-to-one)
        - aggregated: Multiple events to single memory (many-to-one)
        - extracted: Extract key information (one-to-one, filtered)
        - inferred: Infer new knowledge (one-to-one, enhanced)
        """
        from app.models.memory import MemoryCard, MemoryCardCreate

        transformation_type = job.transformation_type
        params = job.processing_params

        if transformation_type == TransformationType.DIRECT.value:
            # Direct transformation: event → memory
            if len(events) != 1:
                raise ValueError("Direct transformation requires exactly one event")

            event = events[0]
            memory_data = MemoryCardCreate(
                memory_type=params.get("memory_type", "episodic"),
                title=params.get("title", f"Event: {event.event_type}"),
                content=params.get("content", event.payload.get("description", str(event.payload))),
                confidence=params.get("confidence", 0.7),
                scope=params.get("scope", event.scope),
                source_events=[event.event_id]
            )

        elif transformation_type == TransformationType.AGGREGATED.value:
            # Aggregate multiple events into one memory
            titles = [e.payload.get("title", e.event_type) for e in events]
            contents = [e.payload.get("content", str(e.payload)) for e in events]

            memory_data = MemoryCardCreate(
                memory_type=params.get("memory_type", "semantic"),
                title=params.get("title", f"Aggregated: {', '.join(titles[:3])}"),
                content=params.get("content", "\n".join(contents)),
                confidence=params.get("confidence", 0.6),
                scope=params.get("scope", events[0].scope if events else "global"),
                source_events=[e.event_id for e in events]
            )

        elif transformation_type == TransformationType.EXTRACTED.value:
            # Extract key information from event
            if len(events) != 1:
                raise ValueError("Extracted transformation requires exactly one event")

            event = events[0]
            key_info = self._extract_key_information(event.payload)

            memory_data = MemoryCardCreate(
                memory_type=params.get("memory_type", "semantic"),
                title=params.get("title", f"Extracted: {key_info.get('title', event.event_type)}"),
                content=params.get("content", key_info.get("content", str(key_info))),
                confidence=params.get("confidence", 0.8),
                scope=params.get("scope", event.scope),
                source_events=[event.event_id]
            )

        elif transformation_type == TransformationType.INFERRED.value:
            # Infer new knowledge from event
            if len(events) != 1:
                raise ValueError("Inferred transformation requires exactly one event")

            event = events[0]
            inferred = self._infer_knowledge(event.payload)

            memory_data = MemoryCardCreate(
                memory_type=params.get("memory_type", "decision"),
                title=params.get("title", f"Inferred: {inferred.get('title', event.event_type)}"),
                content=params.get("content", inferred.get("content", str(inferred))),
                confidence=params.get("confidence", 0.5),  # Lower confidence for inferred
                scope=params.get("scope", event.scope),
                source_events=[event.event_id]
            )

        else:
            raise ValueError(f"Unknown transformation type: {transformation_type}")

        # Create memory using memory repository
        return await self.memory_repo.create_memory(memory_data)

    def _extract_key_information(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract key information from event payload."""
        key_info = {}

        # Common fields to extract
        key_fields = ["title", "subject", "topic", "summary", "conclusion", "result"]

        for field in key_fields:
            if field in payload:
                key_info[field] = payload[field]
                break

        # Extract content
        if "content" in payload:
            key_info["content"] = payload["content"]
        elif "message" in payload:
            key_info["content"] = payload["message"]
        elif "description" in payload:
            key_info["content"] = payload["description"]
        else:
            key_info["content"] = str(payload)

        # Extract title if not found
        if "title" not in key_info:
            key_info["title"] = "Extracted Information"

        return key_info

    def _infer_knowledge(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Infer new knowledge from event payload."""
        inferred = {}

        # Look for patterns that suggest decisions or learning
        if "decision" in payload:
            inferred["title"] = f"Decision: {payload['decision']}"
            inferred["content"] = f"Decision made: {payload['decision']}"
            if "reasoning" in payload:
                inferred["content"] += f"\nReasoning: {payload['reasoning']}"

        elif "learned" in payload or "insight" in payload:
            insight = payload.get("learned", payload.get("insight", ""))
            inferred["title"] = f"Insight: {insight[:50]}..."
            inferred["content"] = f"Learned: {insight}"

        elif "outcome" in payload:
            inferred["title"] = f"Outcome: {payload['outcome']}"
            inferred["content"] = f"Outcome observed: {payload['outcome']}"
            if "cause" in payload:
                inferred["content"] += f"\nCause: {payload['cause']}"

        else:
            inferred["title"] = "Inferred Knowledge"
            inferred["content"] = f"Knowledge inferred from: {list(payload.keys())}"

        return inferred

    async def delete_daydream_job(self, job_id: UUID) -> bool:
        """Delete daydream job by ID."""
        return await self.dream_repo.delete_daydream_job(job_id)

    async def count_daydream_jobs(self, status: str | None = None) -> int:
        """Count daydream jobs."""
        return await self.dream_repo.count_daydream_jobs(status)

    async def get_pending_daydream_jobs(self, limit: int = 50) -> list[DaydreamJob]:
        """Get pending daydream jobs for processing."""
        jobs = await self.dream_repo.get_pending_daydream_jobs(limit)
        return [DaydreamJob.model_validate(j) for j in jobs]

    # Nightdream Operations (Merge, Compress, Deduplicate)

    async def create_nightdream_job(self, job_create: NightdreamJobCreate) -> NightdreamJob:
        """Create a new nightdream job for periodic consolidation."""
        if job_create.operation not in NIGHTDREAM_OPERATIONS:
            raise ValueError(f"Invalid operation: {job_create.operation}")

        job_db = NightdreamJobDB(
            dream_type=DreamType.NIGHTDREAM.value,
            status=DreamStatus.PENDING.value,
            operation=job_create.operation,
            scope=job_create.scope,
            target_memories=job_create.target_memories,
            processing_params=job_create.processing_params,
            scheduled_for=job_create.scheduled_for
        )

        created = await self.dream_repo.create_nightdream_job(job_db)
        return NightdreamJob.model_validate(created)

    async def get_nightdream_job(self, job_id: UUID) -> NightdreamJob | None:
        """Get nightdream job by ID."""
        job = await self.dream_repo.get_nightdream_job(job_id)
        return NightdreamJob.model_validate(job) if job else None

    async def list_nightdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None,
        scope: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[NightdreamJob]:
        """List nightdream jobs."""
        jobs = await self.dream_repo.list_nightdream_jobs(status, operation, scope, limit, offset)
        return [NightdreamJob.model_validate(j) for j in jobs]

    async def delete_nightdream_job(self, job_id: UUID) -> bool:
        """Delete nightdream job by ID."""
        return await self.dream_repo.delete_nightdream_job(job_id)

    async def count_nightdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None
    ) -> int:
        """Count nightdream jobs."""
        return await self.dream_repo.count_nightdream_jobs(status, operation)

    async def get_scheduled_nightdream_jobs(self, limit: int = 50) -> list[NightdreamJob]:
        """Get scheduled nightdream jobs that are due."""
        jobs = await self.dream_repo.get_scheduled_nightdream_jobs(limit)
        return [NightdreamJob.model_validate(j) for j in jobs]

    # Deepdream Operations (Pattern Discovery, Policy Discovery)

    async def create_deepdream_job(self, job_create: DeepdreamJobCreate) -> DeepdreamJob:
        """Create a new deepdream job for strategic analysis."""
        if job_create.operation not in DEEPDREAM_OPERATIONS:
            raise ValueError(f"Invalid operation: {job_create.operation}")

        job_db = DeepdreamJobDB(
            dream_type=DreamType.DEEPDREAM.value,
            status=DreamStatus.PENDING.value,
            operation=job_create.operation,
            scope=job_create.scope,
            analysis_depth=job_create.analysis_depth,
            processing_params=job_create.processing_params
        )

        created = await self.dream_repo.create_deepdream_job(job_db)
        return DeepdreamJob.model_validate(created)

    async def get_deepdream_job(self, job_id: UUID) -> DeepdreamJob | None:
        """Get deepdream job by ID."""
        job = await self.dream_repo.get_deepdream_job(job_id)
        return DeepdreamJob.model_validate(job) if job else None

    async def list_deepdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None,
        scope: str | None = None,
        analysis_depth: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[DeepdreamJob]:
        """List deepdream jobs."""
        jobs = await self.dream_repo.list_deepdream_jobs(status, operation, scope, analysis_depth, limit, offset)
        return [DeepdreamJob.model_validate(j) for j in jobs]

    async def delete_deepdream_job(self, job_id: UUID) -> bool:
        """Delete deepdream job by ID."""
        return await self.dream_repo.delete_deepdream_job(job_id)

    async def count_deepdream_jobs(
        self,
        status: str | None = None,
        operation: str | None = None
    ) -> int:
        """Count deepdream jobs."""
        return await self.dream_repo.count_deepdream_jobs(status, operation)

    async def get_pending_deepdream_jobs(self, limit: int = 50) -> list[DeepdreamJob]:
        """Get pending deepdream jobs."""
        jobs = await self.dream_repo.get_pending_deepdream_jobs(limit)
        return [DeepdreamJob.model_validate(j) for j in jobs]

    # Statistics

    async def get_statistics(self) -> dict[str, Any]:
        """Get dream engine statistics."""
        return await self.dream_repo.get_dream_statistics()
