"""
Evolution Engine - Self-Improvement System

Generates and applies evolution patches based on performance analysis.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from enum import Enum
from collections import defaultdict
import asyncio

from app.darwin.monitoring import PerformanceMonitor, ImprovementTracker, MetricType
from app.darwin.pattern_analysis import PatternAnalyzer, TrendAnalyzer


class EvolutionType(str, Enum):
    """Types of evolutions."""
    MEMORY_PROMOTION = "memory_promotion"
    MEMORY_MERGE = "memory_merge"
    GRAPH_RESTRUCTURE = "graph_restructure"
    PLANNING_TUNING = "planning_tuning"
    GOVERNANCE_CALIBRATION = "governance_calibration"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class EvolutionImpact(str, Enum):
    """Impact level of evolution."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvolutionPatch:
    """
    Represents a proposed evolution patch.
    """

    def __init__(
        self,
        evolution_type: EvolutionType,
        target_component: str,
        description: str,
        changes: Dict[str, Any],
        expected_improvement: float,
        confidence: float,
        impact: EvolutionImpact = EvolutionImpact.MEDIUM,
        rollback_safe: bool = True
    ):
        self.patch_id = uuid4()
        self.evolution_type = evolution_type
        self.target_component = target_component
        self.description = description
        self.changes = changes
        self.expected_improvement = expected_improvement
        self.confidence = confidence
        self.impact = impact
        self.rollback_safe = rollback_safe
        self.applied = False
        self.validated = False
        self.actual_improvement = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "patch_id": str(self.patch_id),
            "evolution_type": self.evolution_type.value,
            "target_component": self.target_component,
            "description": self.description,
            "changes": self.changes,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
            "impact": self.impact.value,
            "rollback_safe": self.rollback_safe,
            "applied": self.applied,
            "validated": self.validated,
            "actual_improvement": self.actual_improvement
        }


class EvolutionEngine:
    """
    Generates and applies evolution patches for self-improvement.
    """

    def __init__(
        self,
        monitor: PerformanceMonitor,
        analyzer: PatternAnalyzer,
        tracker: ImprovementTracker
    ):
        self.monitor = monitor
        self.analyzer = analyzer
        self.tracker = tracker
        self.evolution_history: List[EvolutionPatch] = []
        self.pending_patches: List[EvolutionPatch] = []

    def generate_evolution_patches(self) -> List[EvolutionPatch]:
        """Generate evolution patches based on current analysis."""
        patches = []

        # Analyze patterns
        patterns = self.analyzer.analyze_successful_patterns()

        # Generate patches for each pattern type
        patches.extend(self._generate_memory_patches(patterns["high_performing_memory_types"]))
        patches.extend(self._generate_planning_patches(patterns["successful_planning_strategies"]))
        patches.extend(self._generate_graph_patches(patterns["effective_graph_structures"]))
        patches.extend(self._generate_governance_patches(patterns["optimal_governance_settings"]))

        # Score and prioritize patches
        patches = self._prioritize_patches(patches)

        self.pending_patches = patches
        return patches

    def _generate_memory_patches(self, memory_analysis: List[Dict[str, Any]]) -> List[EvolutionPatch]:
        """Generate memory-related evolution patches."""
        patches = []

        # Find low-performing memory types that should be promoted
        for mem_type in memory_analysis:
            if mem_type["recommendation"] == "PROMOTE_TO_CRITICAL_TIER":
                patch = EvolutionPatch(
                    evolution_type=EvolutionType.MEMORY_PROMOTION,
                    target_component=f"memory_type:{mem_type['memory_type']}",
                    description=f"Promote {mem_type['memory_type']} to critical tier",
                    changes={
                        "memory_type": mem_type["memory_type"],
                        "new_tier": "critical",
                        "reason": f"High performance ({mem_type['mean_performance']:.2f})"
                    },
                    expected_improvement=0.15,
                    confidence=0.85,
                    impact=EvolutionImpact.MEDIUM
                )
                patches.append(patch)

            elif mem_type["recommendation"] == "DEPRECATE_OR_RESTRUCTURE":
                patch = EvolutionPatch(
                    evolution_type=EvolutionType.MEMORY_MERGE,
                    target_component=f"memory_type:{mem_type['memory_type']}",
                    description=f"Merge {mem_type['memory_type']} with related types",
                    changes={
                        "memory_type": mem_type["memory_type"],
                        "action": "merge_with_similar",
                        "reason": f"Low performance ({mem_type['mean_performance']:.2f})"
                    },
                    expected_improvement=0.25,
                    confidence=0.70,
                    impact=EvolutionImpact.HIGH
                )
                patches.append(patch)

        return patches

    def _generate_planning_patches(self, planning_analysis: List[Dict[str, Any]]) -> List[EvolutionPatch]:
        """Generate planning-related evolution patches."""
        patches = []

        # Find high-performing strategies to adopt
        for strategy in planning_analysis:
            if strategy["recommendation"] == "ADOPT_AS_DEFAULT_STRATEGY":
                patch = EvolutionPatch(
                    evolution_type=EvolutionType.PLANNING_TUNING,
                    target_component="planning_engine",
                    description=f"Adopt {strategy['strategy']} as default planning strategy",
                    changes={
                        "new_default_strategy": strategy["strategy"],
                        "success_rate": strategy["success_rate"],
                        "reason": "High success rate demonstrated"
                    },
                    expected_improvement=0.20,
                    confidence=0.90,
                    impact=EvolutionImpact.HIGH
                )
                patches.append(patch)

        return patches

    def _generate_graph_patches(self, graph_analysis: List[Dict[str, Any]]) -> List[EvolutionPatch]:
        """Generate graph-related evolution patches."""
        patches = []

        # Find query types that need optimization
        for query_info in graph_analysis:
            if query_info["recommendation"] == "OPTIMIZE_FOR_THIS_QUERY_TYPE":
                patch = EvolutionPatch(
                    evolution_type=EvolutionType.GRAPH_RESTRUCTURE,
                    target_component=f"graph:query:{query_info['query_type']}",
                    description=f"Optimize graph structure for {query_info['query_type']} queries",
                    changes={
                        "query_type": query_info["query_type"],
                        "optimization": "create_specialized_index",
                        "reason": f"High frequency, can improve speed by {query_info['avg_speed']:.1f} queries/sec"
                    },
                    expected_improvement=0.30,
                    confidence=0.75,
                    impact=EvolutionImpact.MEDIUM
                )
                patches.append(patch)

        return patches

    def _generate_governance_patches(self, governance_analysis: List[Dict[str, Any]]) -> List[EvolutionPatch]:
        """Generate governance-related evolution patches."""
        patches = []

        # Find rules that need adjustment
        for rule_info in governance_analysis:
            if rule_info["recommendation"] == "RELAX_THRESHOLD":
                patch = EvolutionPatch(
                    evolution_type=EvolutionType.GOVERNANCE_CALIBRATION,
                    target_component=f"governance:rule:{rule_info['rule_id']}",
                    description=f"Relax threshold for rule {rule_info['rule_id']}",
                    changes={
                        "rule_id": rule_info["rule_id"],
                        "adjustment": "decrease_sensitivity",
                        "current_fpr": rule_info["false_positive_rate"],
                        "reason": "High false positive rate"
                    },
                    expected_improvement=0.10,
                    confidence=0.80,
                    impact=EvolutionImpact.LOW
                )
                patches.append(patch)

            elif rule_info["recommendation"] == "CAN_STRENGTHEN":
                patch = EvolutionPatch(
                    evolution_type=EvolutionType.GOVERNANCE_CALIBRATION,
                    target_component=f"governance:rule:{rule_info['rule_id']}",
                    description=f"Strengthen rule {rule_info['rule_id']}",
                    changes={
                        "rule_id": rule_info["rule_id"],
                        "adjustment": "increase_sensitivity",
                        "current_fpr": rule_info["false_positive_rate"],
                        "reason": "Very low false positive rate, can be stricter"
                    },
                    expected_improvement=0.05,
                    confidence=0.70,
                    impact=EvolutionImpact.LOW
                )
                patches.append(patch)

        return patches

    def _prioritize_patches(self, patches: List[EvolutionPatch]) -> List[EvolutionPatch]:
        """Prioritize patches by expected impact and confidence."""
        def score(patch: EvolutionPatch) -> float:
            impact_score = {
                EvolutionImpact.CRITICAL: 4.0,
                EvolutionImpact.HIGH: 3.0,
                EvolutionImpact.MEDIUM: 2.0,
                EvolutionImpact.LOW: 1.0
            }[patch.impact]

            return (impact_score * patch.confidence * patch.expected_improvement)

        return sorted(patches, key=score, reverse=True)

    async def apply_patch(self, patch: EvolutionPatch) -> bool:
        """Apply an evolution patch."""
        try:
            # Validate patch is safe to apply
            if not patch.rollback_safe:
                print(f"⚠️  Skipping unsafe patch: {patch.description}")
                return False

            # Simulate application (in real system, would modify actual components)
            print(f"🔄 Applying patch: {patch.description}")
            await asyncio.sleep(0.1)  # Simulate work

            patch.applied = True
            self.evolution_history.append(patch)

            # Record in tracker
            self.tracker.record_evolution(patch.to_dict())

            print(f"✓ Patch applied successfully")
            return True

        except Exception as e:
            print(f"✗ Failed to apply patch: {e}")
            return False

    async def apply_top_n_patches(self, n: int = 5) -> List[EvolutionPatch]:
        """Apply the top N pending patches."""
        if not self.pending_patches:
            return []

        top_patches = self.pending_patches[:n]
        applied = []

        for patch in top_patches:
            if await self.apply_patch(patch):
                applied.append(patch)

        return applied

    def validate_improvements(self) -> Dict[str, Any]:
        """Validate that applied patches produced expected improvements."""
        validation_results = {
            "total_applied": len(self.evolution_history),
            "validated": 0,
            "successful": 0,
            "unsuccessful": 0,
            "details": []
        }

        for patch in self.evolution_history:
            if patch.applied:
                # In real system, would measure actual improvement
                # For demo, simulate validation
                actual_improvement = patch.expected_improvement * (0.8 + 0.2 * hash(str(patch.patch_id)) % 5 / 5)
                patch.actual_improvement = actual_improvement

                success = actual_improvement > 0
                patch.validated = True

                validation_results["validated"] += 1
                if success:
                    validation_results["successful"] += 1
                else:
                    validation_results["unsuccessful"] += 1

                validation_results["details"].append({
                    "patch_id": str(patch.patch_id),
                    "description": patch.description,
                    "expected": patch.expected_improvement,
                    "actual": actual_improvement,
                    "success": success
                })

        return validation_results

    def get_evolution_summary(self) -> Dict[str, Any]:
        """Get summary of all evolutions."""
        return {
            "total_generated": len(self.pending_patches) + len(self.evolution_history),
            "pending": len(self.pending_patches),
            "applied": len(self.evolution_history),
            "by_type": self._count_by_type(),
            "by_impact": self._count_by_impact()
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count patches by evolution type."""
        counts = defaultdict(int)
        for patch in self.evolution_history:
            counts[patch.evolution_type.value] += 1
        return dict(counts)

    def _count_by_impact(self) -> Dict[str, int]:
        """Count patches by impact level."""
        counts = defaultdict(int)
        for patch in self.evolution_history:
            counts[patch.impact.value] += 1
        return dict(counts)
