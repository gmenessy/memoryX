"""
Darwin - Self-Improving AI System

Main system that coordinates monitoring, analysis, and evolution.
"""
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.darwin.monitoring import PerformanceMonitor, ImprovementTracker, MetricType
from app.darwin.pattern_analysis import PatternAnalyzer, TrendAnalyzer
from app.darwin.evolution import EvolutionEngine, EvolutionPatch, EvolutionType, EvolutionImpact


class Darwin:
    """
    Self-improving AI system.

    Darwin monitors its own performance, analyzes patterns,
    and evolves its cognitive architecture for better results.
    """

    def __init__(self, agent_id: str = "darwin"):
        self.agent_id = agent_id
        self.monitor = PerformanceMonitor()
        self.tracker = ImprovementTracker()
        self.analyzer = PatternAnalyzer(self.monitor)
        self.trend_analyzer = TrendAnalyzer(self.monitor)
        self.evolution_engine = EvolutionEngine(
            self.monitor,
            self.analyzer,
            self.tracker
        )

        self.generation = 0
        self.active = False
        self.session_id = None

    def start_session(self) -> str:
        """Start a new Darwin session."""
        self.session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.active = True
        print(f"🧬 Darwin session started: {self.session_id}")
        return self.session_id

    async def process_operation(
        self,
        operation_type: str,
        metric_type: MetricType,
        value: float,
        metadata: Dict[str, Any] = None,
        success: bool = True
    ) -> None:
        """Process an operation and record metrics."""
        if not self.active:
            return

        # Record the metric
        self.monitor.record_metric(
            metric_type=metric_type,
            value=value,
            metadata=metadata or {},
            agent_id=self.agent_id,
            session_id=self.session_id
        )

        # Record operation
        self.monitor.record_operation(operation_type, success)

    async def analyze_and_evolve(self, iterations: int = 100) -> Dict[str, Any]:
        """Run analysis and evolution cycle."""
        print(f"\n🧬 Darwin Generation {self.generation + 1}")
        print("="*60)

        # Set baseline if first generation
        if self.generation == 0:
            baseline = self.monitor.get_performance_summary()
            self.tracker.set_baseline({
                k: v.get("mean", 0.0) for k, v in baseline.items()
                if isinstance(v, dict) and "mean" in v
            })
            print(f"📊 Baseline established")

        # Analyze patterns
        print("🔍 Analyzing patterns...")
        patterns = self.analyzer.analyze_successful_patterns()
        print(f"  ✓ Memory patterns: {len(patterns['high_performing_memory_types'])}")
        print(f"  ✓ Planning strategies: {len(patterns['successful_planning_strategies'])}")
        print(f"  ✓ Graph structures: {len(patterns['effective_graph_structures'])}")
        print(f"  ✓ Governance rules: {len(patterns['optimal_governance_settings'])}")

        # Generate evolution patches
        print("\n🧬 Generating evolution patches...")
        patches = self.evolution_engine.generate_evolution_patches()
        print(f"  ✓ Generated {len(patches)} patches")

        # Apply top patches
        print(f"\n🔄 Applying top 5 patches...")
        applied = await self.evolution_engine.apply_top_n_patches(5)
        print(f"  ✓ Applied {len(applied)} patches")

        # Validate improvements
        print(f"\n📈 Validating improvements...")
        validation = self.evolution_engine.validate_improvements()
        print(f"  ✓ Validated: {validation['validated']}")
        print(f"  ✓ Successful: {validation['successful']}")
        print(f"  ✓ Unsuccessful: {validation['unsuccessful']}")

        # Update current metrics
        current = self.monitor.get_performance_summary()
        self.tracker.update_current({
            k: v.get("mean", 0.0) for k, v in current.items()
            if isinstance(v, dict) and "mean" in v
        })

        # Calculate improvement
        improvement_summary = self.tracker.get_improvement_summary()
        overall_improvement = improvement_summary.get("overall_improvement", 0.0)

        print(f"\n📊 Overall Improvement: {overall_improvement:+.1f}%")

        self.generation += 1

        return {
            "generation": self.generation,
            "patches_generated": len(patches),
            "patches_applied": len(applied),
            "validation": validation,
            "improvement": improvement_summary
        }

    async def run_evolution_cycle(
        self,
        operations_per_cycle: int = 100,
        cycles: int = 5
    ) -> Dict[str, Any]:
        """Run multiple evolution cycles."""
        print(f"\n🧬 DARWIN SELF-IMPROVEMENT CYCLE")
        print("="*70)
        print(f"Operations per cycle: {operations_per_cycle}")
        print(f"Cycles: {cycles}")
        print(f"Agent: {self.agent_id}")
        print(f"Session: {self.session_id}")

        results = {
            "cycles": [],
            "total_improvement": 0.0
        }

        for cycle in range(cycles):
            # Simulate operations
            await self._simulate_operations(operations_per_cycle)

            # Analyze and evolve
            cycle_result = await self.analyze_and_evolve(operations_per_cycle)
            results["cycles"].append(cycle_result)

            # Clear buffer for next cycle
            self.monitor.clear_buffer()

        # Calculate total improvement
        final_summary = self.tracker.get_improvement_summary()
        results["total_improvement"] = final_summary.get("overall_improvement", 0.0)
        results["final_metrics"] = final_summary
        results["evolution_summary"] = self.evolution_engine.get_evolution_summary()

        return results

    async def _simulate_operations(self, count: int) -> None:
        """Simulate operations for testing."""
        import random

        for _ in range(count):
            # Simulate different operation types
            op_type = random.choice([
                "memory_retrieval", "planning", "governance_check", "graph_query"
            ])

            # Generate metrics with some improvement over generations
            base_performance = 0.6 + (self.generation * 0.05)
            improvement_factor = min(0.3, self.generation * 0.03)
            performance = base_performance + improvement_factor + (random.random() * 0.2)

            if op_type == "memory_retrieval":
                await self.process_operation(
                    operation_type="memory_query",
                    metric_type=MetricType.MEMORY_RETRIEVAL,
                    value=min(1.0, performance + random.random() * 0.1),
                    metadata={"memory_type": random.choice(["semantic", "episodic", "procedural"])},
                    success=performance > 0.5
                )

            elif op_type == "planning":
                await self.process_operation(
                    operation_type="plan_execution",
                    metric_type=MetricType.PLANNING_SUCCESS,
                    value=min(1.0, performance + random.random() * 0.05),
                    metadata={"planning_strategy": random.choice(["default", "aggressive", "conservative"])},
                    success=performance > 0.6
                )

                await self.process_operation(
                    operation_type="plan_creation",
                    metric_type=MetricType.PLANNING_SPEED,
                    value=1.0 / (0.5 + random.random() * 2.0),  # Inverse of time
                    metadata={"complexity": random.choice(["low", "medium", "high"])},
                    success=True
                )

            elif op_type == "governance_check":
                await self.process_operation(
                    operation_type="governance_eval",
                    metric_type=MetricType.GOVERNANCE_ACCURACY,
                    value=min(1.0, performance + random.random() * 0.08),
                    metadata={"rule_id": f"rule_{random.randint(1, 10)}", "outcome": random.choice(["true_positive", "true_negative", "false_positive"])},
                    success=performance > 0.7
                )

            elif op_type == "graph_query":
                await self.process_operation(
                    operation_type="graph_traversal",
                    metric_type=MetricType.GRAPH_QUERY_SPEED,
                    value=1.0 / (0.2 + random.random() * 0.8),  # Queries per second
                    metadata={"query_type": random.choice(["bfs", "dfs", "shortest_path"])},
                    success=True
                )

            await asyncio.sleep(0.001)  # Small delay

    def get_status(self) -> Dict[str, Any]:
        """Get current Darwin status."""
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "generation": self.generation,
            "active": self.active,
            "metrics_buffer_size": len(self.monitor.metrics_buffer),
            "evolution_history_size": len(self.evolution_engine.evolution_history),
            "pending_patches": len(self.evolution_engine.pending_patches)
        }

    def shutdown(self) -> None:
        """Shutdown Darwin session."""
        self.active = False
        print(f"\n🧬 Darwin session ended: {self.session_id}")
        print(f"  Final generation: {self.generation}")
        print(f"  Total evolutions: {len(self.evolution_engine.evolution_history)}")
