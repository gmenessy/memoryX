#!/usr/bin/env python3
"""
Quick Demo - BrainDump NextGen Core Systems

A simplified demonstration showing the core capabilities.
"""
import asyncio
from datetime import datetime
from uuid import uuid4
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.services.event_service import EventService
from app.services.memory_service import MemoryService
from app.services.graph_service import GraphService
from app.services.planning_service import PlanningService
from app.models.event import EventCreate, EVENT_TYPES
from app.models.memory import MemoryCardCreate, MEMORY_TYPES
from app.models.graph import NodeType
from app.models.planning import PlanCreate, PlanStatus

from app.logging_config import get_logger

logger = get_logger(__name__)


async def quick_demo():
    """Quick demo of core systems."""
    print("\n" + "="*70)
    print("🚀 BRAINDUMP NEXTGEN - QUICK DEMO")
    print("="*70)

    async with async_session_factory() as session:
        # Phase 1: Event Ingestion
        print("\n📥 PHASE 1: EVENT INGESTION")
        event_service = EventService(session)

        events = [
            EventCreate(
                event_type="user_input",
                actor="developer",
                scope="code_review",
                payload={"action": "commit", "message": "Add authentication"}
            ),
            EventCreate(
                event_type="tool_call",
                actor="ci_system",
                scope="build_123",
                payload={"tool": "pytest", "result": "failed"}
            ),
            EventCreate(
                event_type="decision",
                actor="senior_dev",
                scope="pr_42",
                payload={"decision": "approved", "reason": "good_code"}
            )
        ]

        created_events = []
        for event_data in events:
            event = await event_service.create_event(event_data)
            created_events.append(event)
            print(f"  ✓ Event: {event.event_type} by {event.actor}")

        # Phase 2: Memory Creation
        print("\n🧠 PHASE 2: MEMORY CREATION")
        memory_service = MemoryService(session)

        memories = [
            MemoryCardCreate(
                title="Authentication Best Practice",
                content="Use JWT tokens with async validation",
                memory_type="semantic",
                scope="code_review:auth",
                confidence=0.95
            ),
            MemoryCardCreate(
                title="Test Coverage Requirement",
                content="All new code must have 80%+ test coverage",
                memory_type="governance",
                scope="code_review:quality",
                confidence=0.98
            ),
            MemoryCardCreate(
                title="CI Build Failure Pattern",
                content="Missing imports cause test failures",
                memory_type="risk",
                scope="code_review:common_issues",
                confidence=0.85
            )
        ]

        created_memories = []
        for mem_data in memories:
            memory = await memory_service.create_memory(mem_data)
            created_memories.append(memory)
            print(f"  ✓ Memory: {memory.title} ({memory.memory_type})")

        # Phase 3: Knowledge Graph
        print("\n🕸️  PHASE 3: KNOWLEDGE GRAPH")
        graph_service = GraphService(session)

        # Create nodes
        nodes = [
            ("authentication", NodeType.CONCEPT, "Authentication"),
            ("jwt", NodeType.TECHNIQUE, "JWT Tokens"),
            ("testing", NodeType.PRACTICE, "Testing"),
            ("ci", NodeType.SYSTEM, "CI System")
        ]

        for node_id, node_type, label in nodes:
            await graph_service.create_node(
                node_id=node_id,
                node_type=node_type,
                label=label,
                properties={"domain": "code_review"}
            )
            print(f"  ✓ Node: {label}")

        # Create edges
        await graph_service.create_edge(
            source_id="jwt",
            target_id="authentication",
            edge_type="IMPLEMENTS",
            properties={"strength": 0.9}
        )
        print(f"  ✓ Edge: jwt --IMPLEMENTS--> authentication")

        # Phase 4: Planning
        print("\n🎯 PHASE 4: AUTOMATIC PLANNING")
        planning_service = PlanningService(session)

        plan_data = PlanCreate(
            agent_id="demo_agent",
            goal="Review authentication code for security issues"
        )

        plan = await planning_service.create_plan(plan_data)
        print(f"  ✓ Plan created: {plan.goal}")
        print(f"    Status: {plan.status}")

        # Get tasks
        tasks = await planning_service.get_plan_tasks(plan.plan_id)
        print(f"  ✓ Decomposed into {len(tasks)} tasks:")
        for task in tasks:
            print(f"    - {task.title} [{task.priority.value}]")

        print("\n" + "="*70)
        print("✅ DEMO COMPLETE")
        print("="*70)
        print("\n💡 Core Systems Demonstrated:")
        print("  • Event System: Append-only activity tracking")
        print("  • Memory Cards: Typed information storage")
        print("  • Knowledge Graph: Relationship management")
        print("  • Planning Engine: Goal decomposition")
        print("\n🔗 Explore the full demo: demos/code_review_demo.py")
        print("📚 Documentation: CLAUDE.md, README.md")


if __name__ == "__main__":
    asyncio.run(quick_demo())
