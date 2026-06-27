#!/usr/bin/env python3
"""
Autonomous Code Review System - Demo

This demo showcases BrainDump NextGen's capabilities for building an
intelligent code review system that learns and evolves.
"""
import asyncio
from datetime import datetime
from uuid import uuid4
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.event import Event, EVENT_TYPES
from app.models.memory import MemoryCard, MEMORY_TYPES
from app.models.graph import GraphNode, GraphEdge, NodeType
from app.models.evolution import MemoryPatch, PATCH_TYPES
from app.models.planning import PlanCreate, PlanStatus
from app.models.governance import RuleCreate, RuleSeverity, RuleCondition, RuleAction

from app.services.event_service import EventService
from app.services.memory_service import MemoryService
from app.services.graph_service import GraphService
from app.services.evolution_service import EvolutionService
from app.services.planning_service import PlanningService
from app.services.gatekeeper_service import GatekeeperService
from app.services.governance_service import GovernanceService

from app.logging_config import get_logger

logger = get_logger(__name__)


class CodeReviewDemo:
    """
    Autonomous Code Review System Demo

    Demonstrates:
    1. Event ingestion from code activities
    2. Pattern extraction and memory storage
    3. Graph-based relationship discovery
    4. Evolution of review criteria
    5. Adaptive quality thresholds
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_service = EventService(session)
        self.memory_service = MemoryService(session)
        self.graph_service = GraphService(session)
        self.evolution_service = EvolutionService(session)
        self.planning_service = PlanningService(session)
        self.gatekeeper_service = GatekeeperService(session)
        self.governance_service = GovernanceService(session)

        self.demo_agent_id = "code-review-agent-v1"

    async def run_complete_demo(self):
        """Run the complete code review demo."""
        print("\n" + "="*70)
        print("🔍 AUTONOMOUS CODE REVIEW SYSTEM - DEMO")
        print("="*70)

        # Phase 1: Ingest Code Events
        await self.phase_one_ingest_events()

        # Phase 2: Extract Patterns and Create Memories
        await self.phase_two_extract_patterns()

        # Phase 3: Build Knowledge Graph
        await self.phase_three_build_graph()

        # Phase 4: Evolve Review Criteria
        await self.phase_four_evolve_criteria()

        # Phase 5: Adaptive Review with Planning
        await self.phase_five_adaptive_review()

        # Phase 6: Governance and Quality Control
        await self.phase_five_governance()

        print("\n" + "="*70)
        print("✅ DEMO COMPLETE")
        print("="*70)

    async def phase_one_ingest_events(self):
        """Phase 1: Ingest code events from repository activities."""
        print("\n📥 PHASE 1: INGESTING CODE EVENTS")

        # Simulate various code events using available event types
        events_data = [
            {
                "event_type": "agent_action",
                "actor": "github_integration",
                "scope": "repo:main",
                "payload": {
                    "action": "commit",
                    "commit_hash": "abc123",
                    "author": "developer1",
                    "message": "Fix: Add input validation",
                    "files_changed": ["app/api/user.py"],
                    "lines_added": 15,
                    "lines_deleted": 5,
                    "language": "python"
                }
            },
            {
                "event_type": "tool_call",
                "actor": "github_integration",
                "scope": "pr:42",
                "payload": {
                    "tool": "pull_request",
                    "pr_number": 42,
                    "title": "Implement user authentication",
                    "author": "developer2",
                    "additions": 250,
                    "deletions": 50,
                    "changed_files": 8
                }
            },
            {
                "event_type": "decision",
                "actor": "senior_dev",
                "scope": "pr:42",
                "payload": {
                    "decision": "changes_requested",
                    "comments": [
                        "Missing error handling in auth flow",
                        "Consider using async for database operations"
                    ],
                    "pr_number": 42
                }
            },
            {
                "event_type": "failure",
                "actor": "ci_system",
                "scope": "build:456",
                "payload": {
                    "build_id": "build-456",
                    "error_type": "TypeError",
                    "file": "app/services/auth.py",
                    "line": 42,
                    "message": "NoneType has no attribute 'validate'"
                }
            },
            {
                "event_type": "risk_event",
                "actor": "security_scanner",
                "scope": "scan:daily",
                "payload": {
                    "severity": "HIGH",
                    "cve": "CVE-2024-12345",
                    "file": "app/api/deps.py",
                    "issue": "Potential SQL injection via user input"
                }
            }
        ]

        created_events = []
        for event_data in events_data:
            event = await self.event_service.create_event(
                event_type=event_data["event_type"],
                actor=event_data["actor"],
                scope=event_data["scope"],
                payload=event_data["payload"]
            )
            created_events.append(event)
            print(f"  ✓ Created event: {event.event_type} by {event.actor}")

        print(f"\n📊 Events ingested: {len(created_events)}")
        return created_events

    async def phase_two_extract_patterns(self):
        """Phase 2: Extract patterns and create memory cards."""
        print("\n🧠 PHASE 2: EXTRACTING PATTERNS & CREATING MEMORIES")

        # Pattern extraction from events - using valid memory types
        patterns = [
            {
                "type": "semantic",
                "title": "Input Validation Anti-Pattern",
                "content": "Missing input validation in API endpoints leads to security vulnerabilities. Always validate and sanitize user input.",
                "confidence": 0.95,
                "scope": "code_review:security",
                "metadata": {
                    "language": "python",
                    "severity": "HIGH",
                    "occurrences": 3
                }
            },
            {
                "type": "procedural",
                "title": "Async Database Operations",
                "content": "Use async/await for database operations in FastAPI to prevent blocking the event loop. SQLAlchemy 2.0 with async_session is recommended.",
                "confidence": 0.98,
                "scope": "code_review:best_practices",
                "metadata": {
                    "framework": "fastapi",
                    "database": "sqlalchemy",
                    "pattern": "async_database"
                }
            },
            {
                "type": "risk",
                "title": "Missing Error Handling",
                "content": "Authentication flow lacks proper error handling for edge cases like invalid tokens, expired sessions, and network failures.",
                "confidence": 0.90,
                "scope": "code_review:quality",
                "metadata": {
                    "component": "authentication",
                    "impact": "user_experience"
                }
            },
            {
                "type": "risk",
                "title": "SQL Injection Risk",
                "content": "User input directly passed to database queries without parameterization creates SQL injection vulnerabilities.",
                "confidence": 0.99,
                "scope": "code_review:security",
                "metadata": {
                    "cve": "CVE-2024-12345",
                    "severity": "CRITICAL"
                }
            },
            {
                "type": "semantic",
                "title": "Type Safety Prevents Runtime Errors",
                "content": "Using type hints and proper null checking prevents NoneType attribute errors. The build failure on line 42 could have been prevented.",
                "confidence": 0.92,
                "scope": "code_review:lessons",
                "metadata": {
                    "error_type": "TypeError",
                    "prevention": "type_hints"
                }
            }
        ]

        created_memories = []
        for pattern in patterns:
            memory = await self.memory_service.create_memory(
                title=pattern["title"],
                content=pattern["content"],
                memory_type=pattern["type"],
                scope=pattern["scope"],
                source_events=[],  # Would link to event IDs
                confidence=pattern["confidence"]
            )
            created_memories.append(memory)
            print(f"  ✓ Stored pattern: {pattern['type']} - {pattern['title']}")

        print(f"\n📊 Patterns extracted: {len(created_memories)}")
        return created_memories

    async def phase_three_build_graph(self):
        """Phase 3: Build knowledge graph of code relationships."""
        print("\n🕸️  PHASE 3: BUILDING KNOWLEDGE GRAPH")

        # Create nodes representing code concepts
        nodes_data = [
            ("security-vulnerability", NodeType.CONCEPT, "Security Vulnerability"),
            ("input-validation", NodeType.TECHNIQUE, "Input Validation"),
            ("sql-injection", NodeType.THREAT, "SQL Injection"),
            ("async-pattern", NodeType.PATTERN, "Async/Await Pattern"),
            ("error-handling", NodeType.PRACTICE, "Error Handling"),
            ("type-safety", NodeType.PRINCIPLE, "Type Safety"),
            ("fastapi", NodeType.FRAMEWORK, "FastAPI"),
            ("sqlalchemy", NodeType.LIBRARY, "SQLAlchemy"),
        ]

        created_nodes = {}
        for node_id, node_type, label in nodes_data:
            node = await self.graph_service.create_node(
                node_id=node_id,
                node_type=node_type,
                label=label,
                properties={
                    "domain": "code_review",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            created_nodes[node_id] = node
            print(f"  ✓ Created node: {label} ({node_type.value})")

        # Create relationships
        edges_data = [
            ("input-validation", "security-vulnerability", "PREVENTS", {
                "strength": 0.95,
                "evidence": "prevents_user_input_exploits"
            }),
            ("sql-injection", "security-vulnerability", "IS_A", {
                "severity": "CRITICAL",
                "cve_reference": "CVE-2024-12345"
            }),
            ("input-validation", "sql-injection", "MITIGATES", {
                "effectiveness": 0.90
            }),
            ("async-pattern", "error-handling", "ENHANCES", {
                "benefit": "non_blocking_error_handling"
            }),
            ("type-safety", "error-handling", "PREVENTS", {
                "error_type": "TypeError",
                "effectiveness": 0.85
            }),
            ("fastapi", "async-pattern", "REQUIRES", {
                "reason": "event_loop_compatibility"
            }),
            ("sqlalchemy", "fastapi", "COMPATIBLE_WITH", {
                "version": "2.0+",
                "feature": "async_support"
            }),
        ]

        for source, target, edge_type, properties in edges_data:
            edge = await self.graph_service.create_edge(
                source_id=source,
                target_id=target,
                edge_type=edge_type,
                properties=properties
            )
            print(f"  ✓ Created edge: {source} --{edge_type}--> {target}")

        # Demonstrate graph traversal
        print("\n  🔍 Graph Traversal Demo:")
        vulnerabilities = await self.graph_service.traverse_bfs(
            start_node="sql-injection",
            edge_types=["IS_A"],
            max_depth=2
        )
        print(f"    Found {len(vulnerabilities)} related nodes")

        # Find paths between concepts
        paths = await self.graph_service.find_all_paths(
            source="input-validation",
            target="security-vulnerability",
            max_depth=3
        )
        print(f"    Found {len(paths)} paths from input-validation to security-vulnerability")

        print(f"\n📊 Graph nodes: {len(created_nodes)}, edges created: {len(edges_data)}")
        return created_nodes

    async def phase_four_evolve_criteria(self):
        """Phase 4: Evolve review criteria based on experience."""
        print("\n🔄 PHASE 4: EVOLVING REVIEW CRITERIA")

        # Simulate learning from code review history
        evolution_patches = [
            {
                "patch_type": "update",
                "title": "Lower Threshold for Async Requirement",
                "description": "Based on build failures, increase priority of async patterns",
                "changes": {
                    "async_pattern_threshold": 0.7,  # Lowered from 0.9
                    "reason": "build_failures_observed"
                },
                "fitness_score": 0.88
            },
            {
                "patch_type": "merge",
                "title": "Merge Type Safety with Error Handling",
                "description": "These concepts are closely related in practice",
                "changes": {
                    "merged_concepts": ["type_safety", "error_handling"],
                    "correlation": 0.85
                },
                "fitness_score": 0.92
            },
            {
                "patch_type": "promotion",
                "title": "Promote Input Validation to Critical",
                "description": "Security incidents show this is critical",
                "changes": {
                    "priority_level": "CRITICAL",
                    "justification": "security_incident_CVE_2024_12345"
                },
                "fitness_score": 0.95
            }
        ]

        evolved_memories = []
        for patch_data in evolution_patches:
            # In a real system, would apply to actual memories
            print(f"  ✓ Evolution patch: {patch_data['patch_type']}")
            print(f"    {patch_data['title']}")
            print(f"    Fitness score: {patch_data['fitness_score']}")
            evolved_memories.append(patch_data)

        # Show evolution history
        print("\n  📈 Evolution Statistics:")
        print(f"    Total patches applied: {len(evolution_patches)}")
        avg_fitness = sum(p["fitness_score"] for p in evolution_patches) / len(evolution_patches)
        print(f"    Average fitness improvement: {avg_fitness:.2f}")

        return evolved_memories

    async def phase_five_adaptive_review(self):
        """Phase 5: Adaptive review with planning system."""
        print("\n🎯 PHASE 5: ADAPTIVE REVIEW WITH PLANNING")

        # Create a comprehensive review plan
        plan_data = PlanCreate(
            agent_id=self.demo_agent_id,
            goal="Perform comprehensive security and quality review on authentication module",
            plan_data={
                "review_type": "comprehensive",
                "target_module": "authentication",
                "priority": "HIGH"
            }
        )

        plan = await self.planning_service.create_plan(plan_data)
        print(f"  ✓ Created review plan: {plan.plan_id}")
        print(f"    Goal: {plan.goal}")

        # Get decomposed tasks
        tasks = await self.planning_service.get_plan_tasks(plan.plan_id)
        print(f"  ✓ Plan decomposed into {len(tasks)} tasks:")
        for task in tasks:
            print(f"    - {task.title} ({task.task_type}) [Priority: {task.priority.value}]")

        # Simulate plan execution
        print("\n  ⚡ Executing review plan...")
        from app.models.planning import PlanExecutionRequest

        execution_result = await self.planning_service.execute_plan(
            PlanExecutionRequest(
                plan_id=plan.plan_id,
                max_parallel_tasks=3,
                continue_on_failure=True
            )
        )

        print(f"  ✓ Review complete:")
        print(f"    Tasks executed: {execution_result.total_tasks}")
        print(f"    Completed: {execution_result.completed_tasks}")
        print(f"    Failed: {execution_result.failed_tasks}")
        print(f"    Duration: {execution_result.execution_duration:.2f}s")

        return plan, execution_result

    async def phase_five_governance(self):
        """Phase 6: Governance and quality control."""
        print("\n🛡️  PHASE 6: GOVERNANCE & QUALITY CONTROL")

        # Create governance rules for code review
        rules = [
            RuleCreate(
                name="Critical Security Review Required",
                description="All code changes touching security-sensitive areas must undergo security review",
                conditions=[
                    RuleCondition(
                        field="files_changed",
                        operator="contains",
                        value=["auth", "security", "user", "session"]
                    )
                ],
                actions=[
                    RuleAction(
                        type="require_review",
                        parameters={"reviewer_type": "security_expert", "min_approvers": 2}
                    )
                ],
                severity=RuleSeverity.CRITICAL,
                enabled=True
            ),
            RuleCreate(
                name="Async Pattern Enforcement",
                description="Database operations must use async patterns",
                conditions=[
                    RuleCondition(
                        field="functions_changed",
                        operator="contains",
                        value=["db.", "database.", "repository."]
                    )
                ],
                actions=[
                    RuleAction(
                        type="validate_pattern",
                        parameters={"required_pattern": "async def", "if_missing": "flag_for_review"}
                    )
                ],
                severity=RuleSeverity.HIGH,
                enabled=True
            ),
            RuleCreate(
                name="Type Safety Check",
                description="New code must include type hints",
                conditions=[
                    RuleCondition(
                        field="language",
                        operator="equals",
                        value="python"
                    )
                ],
                actions=[
                    RuleAction(
                        type="check_coverage",
                        parameters={"min_type_hint_coverage": 0.8}
                    )
                ],
                severity=RuleSeverity.MEDIUM,
                enabled=True
            )
        ]

        created_rules = []
        for rule in rules:
            created_rule = await self.governance_service.create_rule(rule)
            created_rules.append(created_rule)
            print(f"  ✓ Created rule: {rule.name}")
            print(f"    Severity: {rule.severity.value}")
            print(f"    Conditions: {len(rule.conditions)}")
            print(f"    Actions: {len(rule.actions)}")

        # Simulate rule evaluation
        print("\n  🔬 Evaluating rules against sample code...")
        sample_context = {
            "files_changed": ["app/services/auth.py", "app/api/user.py"],
            "functions_changed": ["async def get_user", "db.session.query"],
            "language": "python",
            "type_hint_coverage": 0.75
        }

        triggered_rules = []
        for rule in created_rules:
            # Check if rule conditions match
            if rule.enabled:
                triggered = await self.governance_service.evaluate_rule(
                    rule.rule_id,
                    sample_context
                )
                if triggered:
                    triggered_rules.append(rule)
                    print(f"    ⚠️  Rule triggered: {rule.name}")

        print(f"\n  📊 Governance Summary:")
        print(f"    Total rules: {len(created_rules)}")
        print(f"    Rules triggered: {len(triggered_rules)}")

        return created_rules


async def main():
    """Run the complete code review demo."""
    async with async_session_factory() as session:
        demo = CodeReviewDemo(session)
        await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())
