"""
Pattern Analysis Algorithms

Analyzes performance patterns to identify improvement opportunities.
"""
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import statistics

from app.darwin.monitoring import MetricType, PerformanceMonitor


class PatternAnalyzer:
    """
    Analyzes performance patterns to identify what works and what doesn't.
    """

    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor

    def analyze_successful_patterns(self) -> Dict[str, Any]:
        """Analyze patterns that lead to successful outcomes."""
        patterns = {
            "high_performing_memory_types": self._analyze_memory_performance(),
            "successful_planning_strategies": self._analyze_planning_success(),
            "effective_graph_structures": self._analyze_graph_effectiveness(),
            "optimal_governance_settings": self._analyze_governance_optimization()
        }
        return patterns

    def _analyze_memory_performance(self) -> List[Dict[str, Any]]:
        """Analyze which memory types perform best."""
        # Group metrics by memory type metadata
        memory_performance = defaultdict(list)

        for metric in self.monitor.metrics_buffer:
            if metric["metric_type"] == MetricType.MEMORY_RETRIEVAL:
                memory_type = metric["metadata"].get("memory_type", "unknown")
                memory_performance[memory_type].append(metric["value"])

        # Calculate statistics per memory type
        results = []
        for memory_type, values in memory_performance.items():
            if len(values) >= 5:  # Minimum samples
                results.append({
                    "memory_type": memory_type,
                    "mean_performance": statistics.mean(values),
                    "sample_count": len(values),
                    "stability": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "recommendation": self._get_memory_recommendation(
                        memory_type,
                        statistics.mean(values)
                    )
                })

        # Sort by performance
        results.sort(key=lambda x: x["mean_performance"], reverse=True)
        return results

    def _analyze_planning_success(self) -> List[Dict[str, Any]]:
        """Analyze which planning strategies are most successful."""
        planning_performance = defaultdict(list)

        for metric in self.monitor.metrics_buffer:
            if metric["metric_type"] == MetricType.PLANNING_SUCCESS:
                strategy = metric["metadata"].get("planning_strategy", "default")
                planning_performance[strategy].append(metric["value"])

        results = []
        for strategy, values in planning_performance.items():
            if len(values) >= 5:
                results.append({
                    "strategy": strategy,
                    "success_rate": statistics.mean(values),
                    "sample_count": len(values),
                    "recommendation": self._get_planning_recommendation(
                        strategy,
                        statistics.mean(values)
                    )
                })

        results.sort(key=lambda x: x["success_rate"], reverse=True)
        return results

    def _analyze_graph_effectiveness(self) -> List[Dict[str, Any]]:
        """Analyze which graph structures are most effective."""
        graph_performance = defaultdict(list)

        for metric in self.monitor.metrics_buffer:
            if metric["metric_type"] == MetricType.GRAPH_QUERY_SPEED:
                query_type = metric["metadata"].get("query_type", "default")
                graph_performance[query_type].append(1.0 / metric["value"])  # Convert to queries/sec

        results = []
        for query_type, speeds in graph_performance.items():
            if len(speeds) >= 5:
                results.append({
                    "query_type": query_type,
                    "avg_speed": statistics.mean(speeds),
                    "sample_count": len(speeds),
                    "recommendation": self._get_graph_recommendation(
                        query_type,
                        statistics.mean(speeds)
                    )
                })

        results.sort(key=lambda x: x["avg_speed"], reverse=True)
        return results

    def _analyze_governance_optimization(self) -> List[Dict[str, Any]]:
        """Analyze governance rule effectiveness."""
        governance_performance = defaultdict(lambda: {"true_positives": 0, "false_positives": 0, "total": 0})

        for metric in self.monitor.metrics_buffer:
            if metric["metric_type"] == MetricType.GOVERNANCE_ACCURACY:
                rule_id = metric["metadata"].get("rule_id", "unknown")
                outcome = metric["metadata"].get("outcome", "unknown")

                governance_performance[rule_id]["total"] += 1
                if outcome == "true_positive":
                    governance_performance[rule_id]["true_positives"] += 1
                elif outcome == "false_positive":
                    governance_performance[rule_id]["false_positives"] += 1

        results = []
        for rule_id, stats in governance_performance.items():
            if stats["total"] >= 10:
                precision = stats["true_positives"] / stats["total"] if stats["total"] > 0 else 0
                false_positive_rate = stats["false_positives"] / stats["total"] if stats["total"] > 0 else 0

                results.append({
                    "rule_id": rule_id,
                    "precision": precision,
                    "false_positive_rate": false_positive_rate,
                    "total_evaluations": stats["total"],
                    "recommendation": self._get_governance_recommendation(
                        false_positive_rate
                    )
                })

        results.sort(key=lambda x: x["precision"], reverse=True)
        return results

    def _get_memory_recommendation(self, memory_type: str, performance: float) -> str:
        """Get recommendation for memory type."""
        if performance >= 0.9:
            return "PROMOTE_TO_CRITICAL_TIER"
        elif performance >= 0.7:
            return "MAINTAIN_CURRENT_LEVEL"
        elif performance >= 0.5:
            return "CONSIDER_OPTIMIZATION"
        else:
            return "DEPRECATE_OR_RESTRUCTURE"

    def _get_planning_recommendation(self, strategy: str, success_rate: float) -> str:
        """Get recommendation for planning strategy."""
        if success_rate >= 0.9:
            return "ADOPT_AS_DEFAULT_STRATEGY"
        elif success_rate >= 0.7:
            return "USE_FOR_SPECIFIC_DOMAINS"
        else:
            return "REPLACE_OR_TUNING_NEEDED"

    def _get_graph_recommendation(self, query_type: str, speed: float) -> str:
        """Get recommendation for graph structure."""
        if speed >= 100:  # 100+ queries/sec
            return "OPTIMIZE_FOR_THIS_QUERY_TYPE"
        elif speed >= 50:
            return "CONSIDER_CACHING"
        else:
            return "RESTRUCTURE_INDEXING"

    def _get_governance_recommendation(self, false_positive_rate: float) -> str:
        """Get recommendation for governance rule."""
        if false_positive_rate > 0.15:
            return "RELAX_THRESHOLD"
        elif false_positive_rate < 0.05:
            return "CAN_STRENGTHEN"
        else:
            return "MAINTAIN_CURRENT"

    def identify_correlations(self) -> List[Dict[str, Any]]:
        """Identify correlations between different metrics."""
        correlations = []

        # Collect all metrics by type
        metric_values = defaultdict(list)
        for metric in self.monitor.metrics_buffer:
            metric_values[metric["metric_type"]].append({
                "value": metric["value"],
                "timestamp": metric["timestamp"],
                "metadata": metric["metadata"]
            })

        # Check for correlations between planning success and memory retrieval
        if MetricType.PLANNING_SUCCESS.value in metric_values and \
           MetricType.MEMORY_RETRIEVAL.value in metric_values:

            planning_success = metric_values[MetricType.PLANNING_SUCCESS.value]
            memory_retrieval = metric_values[MetricType.MEMORY_RETRIEVAL.value]

            # Simple correlation check
            if len(planning_success) >= 10 and len(memory_retrieval) >= 10:
                correlation = self._calculate_correlation(
                    [m["value"] for m in planning_success],
                    [m["value"] for m in memory_retrieval[:len(planning_success)]]
                )

                if abs(correlation) > 0.5:
                    correlations.append({
                        "metric_1": "planning_success",
                        "metric_2": "memory_retrieval",
                        "correlation": correlation,
                        "interpretation": self._interpret_correlation(correlation)
                    })

        return correlations

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = min(len(x), len(y))
        if n < 2:
            return 0.0

        x = x[:n]
        y = y[:n]

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        denominator_y = sum((y[i] - mean_y) ** 2 for i in range(n))

        if denominator_x == 0 or denominator_y == 0:
            return 0.0

        return numerator / (denominator_x * denominator_y) ** 0.5

    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation coefficient."""
        if correlation > 0.7:
            return "STRONG_POSITIVE"
        elif correlation > 0.3:
            return "MODERATE_POSITIVE"
        elif correlation > -0.3:
            return "WEAK_OR_NONE"
        elif correlation > -0.7:
            return "MODERATE_NEGATIVE"
        else:
            return "STRONG_NEGATIVE"


class TrendAnalyzer:
    """
    Analyzes performance trends over time.
    """

    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor

    def analyze_trends(self, metric_type: MetricType, window_hours: int = 24) -> Dict[str, Any]:
        """Analyze trends for a specific metric over time."""
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)

        values = [
            (m["timestamp"], m["value"])
            for m in self.monitor.metrics_buffer
            if m["metric_type"] == metric_type.value and m["timestamp"] >= cutoff
        ]

        if len(values) < 5:
            return {"trend": "INSUFFICIENT_DATA", "values": len(values)}

        # Sort by timestamp
        values.sort(key=lambda x: x[0])

        # Extract just the values
        numeric_values = [v[1] for v in values]

        # Calculate trend
        first_half = numeric_values[:len(numeric_values)//2]
        second_half = numeric_values[len(numeric_values)//2:]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        trend = (second_avg - first_avg) / first_avg if first_avg > 0 else 0

        return {
            "trend": "IMPROVING" if trend > 0.01 else "DECLINING" if trend < -0.01 else "STABLE",
            "trend_percent": trend * 100,
            "first_half_avg": first_avg,
            "second_half_avg": second_avg,
            "sample_count": len(values),
            "window_hours": window_hours
        }

    def detect_anomalies(self, metric_type: MetricType, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalous values using standard deviation."""
        cutoff = datetime.utcnow() - timedelta(hours=24)

        values = [
            m for m in self.monitor.metrics_buffer
            if m["metric_type"] == metric_type.value and m["timestamp"] >= cutoff
        ]

        if len(values) < 10:
            return []

        numeric_values = [m["value"] for m in values]
        mean = statistics.mean(numeric_values)
        std = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0

        anomalies = []
        for value_obj in values:
            z_score = (value_obj["value"] - mean) / std if std > 0 else 0
            if abs(z_score) > threshold_std:
                anomalies.append({
                    "timestamp": value_obj["timestamp"],
                    "value": value_obj["value"],
                    "z_score": z_score,
                    "expected_range": (mean - threshold_std * std, mean + threshold_std * std),
                    "metadata": value_obj["metadata"]
                })

        return anomalies
