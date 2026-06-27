#!/usr/bin/env python3
"""
Simple Demo - BrainDump NextGen

A minimal demonstration showing key capabilities.
"""
import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.database import Base
from app.models.event import EventDB
from app.models.memory import MemoryCardDB
from app.models.graph import GraphNodeDB, GraphEdgeDB
from app.models.planning import PlanDB, TaskDB

from app.logging_config import get_logger

logger = get_logger(__name__)


async def simple_demo():
    """Simple demo showing core capabilities."""
    print("\n" + "="*70)
    print("🚀 BRAINDUMP NEXTGEN - SIMPLE DEMO")
    print("="*70)

    # Create in-memory database
    test_db = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_db.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(
        test_db, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        # Phase 1: Create Events
        print("\n📥 PHASE 1: EVENT SYSTEM")
        print("  • Creating code review events...")

        event1 = EventDB(
            event_type="user_input",
            actor="developer",
            scope="code_review",
            payload={"action": "commit", "message": "Add authentication"}
        )
        session.add(event1)

        event2 = EventDB(
            event_type="decision",
            actor="senior_dev",
            scope="pr_42",
            payload={"decision": "approved", "reason": "good_code"}
        )
        session.add(event2)

        await session.commit()
        print(f"  ✓ Created 2 events (append-only truth layer)")

        # Phase 2: Create Memories
        print("\n🧠 PHASE 2: MEMORY CARDS")
        print("  • Storing learned patterns...")

        memory1 = MemoryCardDB(
            memory_type="semantic",
            title="JWT Authentication Pattern",
            content="Use JWT tokens with async validation for secure auth",
            confidence=0.95,
            scope="code_review:auth"
        )
        session.add(memory1)

        memory2 = MemoryCardDB(
            memory_type="governance",
            title="Code Review Policy",
            content="All PRs must have 80%+ test coverage",
            confidence=0.98,
            scope="code_review:quality"
        )
        session.add(memory2)

        await session.commit()
        print(f"  ✓ Created 2 memory cards (typed storage)")

        # Phase 3: Build Graph
        print("\n🕸️  PHASE 3: KNOWLEDGE GRAPH")
        print("  • Building relationship network...")

        node1 = GraphNodeDB(
            node_id="jwt",
            node_type="technique",
            label="JWT Tokens",
            properties={"category": "auth"}
        )
        session.add(node1)

        node2 = GraphNodeDB(
            node_id="auth",
            node_type="concept",
            label="Authentication",
            properties={"category": "security"}
        )
        session.add(node2)

        edge1 = GraphEdgeDB(
            source_id="jwt",
            target_id="auth",
            edge_type="IMPLEMENTS",
            properties={"strength": 0.9}
        )
        session.add(edge1)

        await session.commit()
        print(f"  ✓ Created 2 nodes, 1 edge (relationship graph)")

        # Phase 4: Planning
        print("\n🎯 PHASE 4: PLANNING ENGINE")
        print("  • Decomposing goal into tasks...")

        plan = PlanDB(
            agent_id="review_agent",
            goal="Review authentication code",
            status="active",
            progress=0.0,
            plan_data={"priority": "high"}
        )
        session.add(plan)
        await session.flush()

        task1 = TaskDB(
            plan_id=plan.plan_id,
            title="Check for security vulnerabilities",
            task_type="security_scan",
            status="pending",
            priority="high"
        )
        session.add(task1)

        task2 = TaskDB(
            plan_id=plan.plan_id,
            title="Verify async patterns",
            task_type="code_check",
            status="pending",
            priority="medium"
        )
        session.add(task2)

        await session.commit()
        print(f"  ✓ Created plan with 2 tasks (goal decomposition)")

        print("\n" + "="*70)
        print("✅ DEMO COMPLETE")
        print("="*70)

        print("\n💡 BrainDump NextGen Core Systems Demonstrated:")
        print("  1. Event System      - Append-only activity tracking")
        print("  2. Memory Cards      - Typed information storage")
        print("  3. Knowledge Graph   - Relationship management")
        print("  4. Planning Engine   - Goal decomposition")
        print("\n🎯 'One More Thing' Demo Proposal:")
        print("  See: demos/ONE_MORE_THING.md")
        print("\n📚 Full documentation: CLAUDE.md")


if __name__ == "__main__":
    asyncio.run(simple_demo())
