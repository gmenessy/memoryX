"""
Database Query Optimization and Monitoring

Provides query performance tracking and optimization suggestions.
"""
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger

logger = get_logger(__name__)


class QueryStats:
    """Statistics for database queries."""

    def __init__(self):
        self.queries: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.slow_queries: List[Dict[str, Any]] = []
        self.max_history = 1000

    def record_query(
        self,
        query: str,
        duration_ms: float,
        params: Any = None,
        error: Optional[str] = None
    ):
        """Record a query execution."""
        query_hash = hash(query)
        stats = {
            "query": query,
            "query_hash": query_hash,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow(),
            "params": str(params)[:200] if params else None,
            "error": error
        }

        query_type = self._classify_query(query)
        self.queries[query_type].append(stats)

        if duration_ms > 100:  # Slow query threshold
            self.slow_queries.append(stats)

        # Trim history
        if len(self.queries[query_type]) > self.max_history:
            self.queries[query_type].pop(0)
        if len(self.slow_queries) > self.max_history:
            self.slow_queries.pop(0)

    def _classify_query(self, query: str) -> str:
        """Classify query type."""
        query_upper = query.strip().upper()
        if query_upper.startswith("SELECT"):
            return "SELECT"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        elif query_upper.startswith("CREATE"):
            return "CREATE"
        elif query_upper.startswith("ALTER"):
            return "ALTER"
        else:
            return "OTHER"

    def get_stats(self, query_type: str = None) -> Dict[str, Any]:
        """Get statistics for query type."""
        if query_type and query_type not in self.queries:
            return {}

        target_queries = self.queries[query_type] if query_type else [
            q for queries in self.queries.values() for q in queries
        ]

        if not target_queries:
            return {}

        durations = [q["duration_ms"] for q in target_queries]

        return {
            "count": len(target_queries),
            "total_duration_ms": sum(durations),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "slow_count": len([d for d in durations if d > 100])
        }

    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get slowest queries."""
        return sorted(
            self.slow_queries,
            key=lambda x: x["duration_ms"],
            reverse=True
        )[:limit]

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Generate optimization suggestions."""
        suggestions = []

        # Check for slow SELECT queries
        select_stats = self.get_stats("SELECT")
        if select_stats and select_stats["avg_duration_ms"] > 50:
            suggestions.append({
                "type": "query_optimization",
                "priority": "HIGH",
                "message": f"Average SELECT duration is {select_stats['avg_duration_ms']:.1f}ms. Consider adding indexes.",
                "suggestion": "Review indexes on frequently queried columns"
            })

        # Check for slow query patterns
        for query_type, stats_dict in self.queries.items():
            if not stats_dict:
                continue

            # Check for N+1 pattern (many similar queries)
            query_signatures = defaultdict(int)
            for q in stats_dict:
                # Simplified signature (remove parameter values)
                signature = q["query"][:100]
                query_signatures[signature] += 1

            for sig, count in query_signatures.items():
                if count > 50:  # Potential N+1
                    suggestions.append({
                        "type": "n_plus_one",
                        "priority": "MEDIUM",
                        "message": f"Potential N+1 query pattern: {count} similar queries",
                        "suggestion": "Consider using eager loading or batch queries"
                    })
                    break

        return suggestions


class DatabaseOptimizer:
    """
    Database query optimization and monitoring.
    """

    def __init__(self, slow_query_threshold_ms: float = 100.0):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.query_stats = QueryStats()
        self.index_recommendations: List[Dict[str, Any]] = []

    def setup_query_monitoring(self, engine: Engine):
        """Setup query monitoring for SQLAlchemy engine."""
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
            context._query_start_time = time.perf_counter()

        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
            if hasattr(context, '_query_start_time'):
                duration_ms = (time.perf_counter() - context._query_start_time) * 1000
                self.query_stats.record_query(statement, duration_ms, params)

                if duration_ms > self.slow_query_threshold_ms:
                    logger.warning(
                        f"Slow query detected ({duration_ms:.1f}ms): {statement[:200]}"
                    )

    def analyze_indexes(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Analyze and recommend indexes."""
        recommendations = []

        # Get slow queries
        slow_queries = self.query_stats.get_slow_queries(limit=100)

        # Analyze query patterns
        table_query_counts = defaultdict(int)
        column_query_counts = defaultdict(int)

        for sq in slow_queries:
            query = sq["query"].upper()

            # Extract table names (simplified)
            if "FROM" in query:
                from_part = query.split("FROM")[1].split()[0]
                table_query_counts[from_part] += 1

            # Look for WHERE clauses
            if "WHERE" in query:
                where_part = query.split("WHERE")[1].split("LIMIT")[0].split("ORDER")[0].split("GROUP")[0]
                # Simple column extraction
                for word in where_part.split():
                    if word.strip() and not word.startswith(("AND", "OR", "=", ">", "<")):
                        column_query_counts[word.strip()] += 1

        # Generate recommendations
        for table, count in table_query_counts.items():
            if count > 20:
                recommendations.append({
                    "table": table,
                    "type": "table_index",
                    "priority": "HIGH" if count > 100 else "MEDIUM",
                    "reason": f"Queried {count} times in slow queries"
                })

        self.index_recommendations = recommendations
        return recommendations

    def get_query_performance_summary(self) -> Dict[str, Any]:
        """Get overall query performance summary."""
        all_stats = self.query_stats.get_stats()

        return {
            "total_queries": all_stats.get("count", 0),
            "avg_duration_ms": all_stats.get("avg_duration_ms", 0),
            "slow_query_count": all_stats.get("slow_count", 0),
            "slow_query_threshold_ms": self.slow_query_threshold_ms,
            "optimization_suggestions": len(self.query_stats.get_optimization_suggestions()),
            "index_recommendations": len(self.index_recommendations)
        }

    def optimize_query(self, query: str) -> str:
        """Simple query optimization suggestions."""
        suggestions = []

        query_upper = query.upper()

        # Check for SELECT *
        if "SELECT *" in query_upper:
            suggestions.append("Avoid SELECT * - specify only needed columns")

        # Check for missing LIMIT
        if "SELECT" in query_upper and "LIMIT" not in query_upper:
            suggestions.append("Consider adding LIMIT to prevent large result sets")

        # Check for ORDER BY without index hint
        if "ORDER BY" in query_upper and "LIMIT" in query_upper:
            suggestions.append("Ensure ORDER BY columns are indexed for pagination performance")

        return "\n".join(suggestions) if suggestions else "Query looks good"


class ConnectionPoolMonitor:
    """Monitor database connection pool health."""

    def __init__(self):
        self.pool_stats: List[Dict[str, Any]] = []

    def record_pool_status(self, pool) -> Dict[str, Any]:
        """Record current pool status."""
        status = {
            "timestamp": datetime.utcnow(),
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": getattr(pool, '_max_overflow', 0)
        }

        self.pool_stats.append(status)
        if len(self.pool_stats) > 100:
            self.pool_stats.pop(0)

        return status

    def get_pool_utilization(self) -> Dict[str, Any]:
        """Get pool utilization statistics."""
        if not self.pool_stats:
            return {}

        latest = self.pool_stats[-1]
        total = latest["size"] + latest["max_overflow"]

        return {
            "current_size": latest["size"],
            "checked_out": latest["checked_out"],
            "checked_in": latest["checked_in"],
            "utilization_percent": (latest["checked_out"] / total * 100) if total > 0 else 0,
            "overflow_in_use": latest["overflow"]
        }
