#!/usr/bin/env python3
"""
Darwin Demo - Self-Improving AI System

A live demonstration of an AI system that evolves its own architecture.
"""
import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.darwin.darwin import Darwin
from app.darwin.monitoring import MetricType


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{title}")
    print("-"*70)


async def demonstrate_darwin() -> None:
    """Demonstrate Darwin's self-improvement capabilities."""

    print_header("🧬 DARWIN - SELF-IMPROVING AI SYSTEM")

    print("""
🧬 What makes this special?

Darwin doesn't just USE an AI system - it IMPROVES itself.
It analyzes its own performance, identifies patterns, and evolves
its cognitive architecture for better results.

    """)

    # Initialize Darwin
    darwin = Darwin(agent_id="darwin_demo_v1")

    # Start session
    session_id = darwin.start_session()

    print_section("📊 BASELINE PERFORMANCE")

    print("""
Let's establish a baseline. Darwin will perform 100 operations
across different system components:
    """)

    # Simulate baseline operations
    print("  Running baseline operations...")
    await darwin._simulate_operations(100)

    baseline_summary = darwin.monitor.get_performance_summary()
    print(f"\n  Baseline Results:")
    print(f"    Memory Retrieval: {baseline_summary.get('memory_retrieval', {}).get('mean', 0):.2f}")
    print(f"    Planning Success: {baseline_summary.get('planning_success', {}).get('mean', 0):.2f}")
    print(f"    Governance Accuracy: {baseline_summary.get('governance_accuracy', {}).get('mean', 0):.2f}")

    # Set baseline
    darwin.tracker.set_baseline({
        k: v.get("mean", 0.0) for k, v in baseline_summary.items()
        if isinstance(v, dict) and "mean" in v
    })

    print_section("🧬 EVOLUTION CYCLES")

    print("""
Now Darwin will run 3 evolution cycles. Each cycle:
1. Performs 100 operations
2. Analyzes patterns
3. Generates evolution patches
4. Applies top improvements
5. Validates results

Let's watch it learn...
    """)

    # Run evolution cycles
    results = await darwin.run_evolution_cycle(
        operations_per_cycle=100,
        cycles=3
    )

    print_section("📈 EVOLUTION RESULTS")

    print(f"\n  Cycles Completed: {len(results['cycles'])}")
    print(f"  Total Patches Generated: {results['evolution_summary']['total_generated']}")
    print(f"  Patches Applied: {results['evolution_summary']['applied']}")

    print("\n  Generation-by-Generation:")
    for i, cycle in enumerate(results['cycles'], 1):
        print(f"\n    Generation {i}:")
        print(f"      Patches Applied: {cycle['patches_applied']}")
        if cycle.get('improvement'):
            print(f"      Improvement: {cycle['improvement'].get('overall_improvement', 0):+.1f}%")

    print_section("✨ FINAL RESULTS")

    final_metrics = results['final_metrics']

    print(f"\n  📊 Performance Comparison:")
    for metric_type, data in final_metrics.get('metrics', {}).items():
        baseline = data.get('baseline', 0)
        current = data.get('current', 0)
        improvement = data.get('improvement_percent', 0)

        print(f"\n    {metric_type}:")
        print(f"      Before: {baseline:.2f}")
        print(f"      After:  {current:.2f}")
        print(f"      Change: {improvement:+.1f}%")

    overall = results.get('total_improvement', 0)
    print(f"\n  🎯 Overall Improvement: {overall:+.1f}%")

    print_section("🎭 ONE MORE THING")

    print(f"""
And here's the best part...

The improvements you just saw?
They were designed by the PREVIOUS version of Darwin.

Each generation improves itself to the point where it can
design BETTER improvements for the next generation.

This is the power of BrainDump NextGen:

✓ Systems that LEARN how they learn best
✓ Architectures that OPTIMIZE themselves
✓ Intelligence that EVOLVES its own evolution

    """)

    print_section("🧬 DARWIN STATUS")

    status = darwin.get_status()
    print(f"  Agent: {status['agent_id']}")
    print(f"  Generation: {status['generation']}")
    print(f"  Evolutions Applied: {status['evolution_history_size']}")

    darwin.shutdown()

    print_header("🧬 END OF DEMO")

    print("""
Ready to build your own self-improving systems?

Check out:
  • app/darwin/ - Darwin implementation
  • demos/ONE_MORE_THING.md - Full proposal
  • CLAUDE.md - Project documentation

    """)


async def quick_darwin_demo() -> None:
    """Quick Darwin demo for testing."""
    print("\n🧬 Quick Darwin Demo\n")

    darwin = Darwin(agent_id="quick_darwin")
    darwin.start_session()

    # Run one cycle
    result = await darwin.run_evolution_cycle(
        operations_per_cycle=50,
        cycles=2
    )

    print(f"\n✓ Complete! Improvement: {result.get('total_improvement', 0):+.1f}%")

    darwin.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(demonstrate_darwin())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
