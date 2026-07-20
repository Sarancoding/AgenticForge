"""
Metrics collector — tracks latency, token usage, cost, loop iterations,
and failure rates across all agent executions. Exposes Prometheus-style
endpoints and in-memory rolling window for the Streamlit dashboard.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricPoint:
    """A single data point in the metrics stream."""

    timestamp: float
    value: float
    labels: dict = field(default_factory=dict)


@dataclass
class AgentMetricsSnapshot:
    """Snapshot of metrics for a single agent execution."""

    agent_type: str
    latency_ms: float = 0.0
    token_count: int = 0
    cost_usd: float = 0.0
    iterations: int = 0
    success: bool = True
    error: str | None = None


class MetricsCollector:
    """
    In-memory metrics collector with rolling windows.

    Tracks:
    - Per-agent latency (p50, p95, p99)
    - Token usage and estimated cost
    - Loop iterations per execution
    - Success/failure rates
    - Per-second throughput

    Data is retained in configurable rolling windows for dashboard display.
    """

    def __init__(self, window_seconds: int = 300) -> None:
        """
        Args:
            window_seconds: Rolling window retention in seconds (default 5 min).
        """
        self.window_seconds = window_seconds
        self._latencies: deque[MetricPoint] = deque()
        self._token_usage: deque[MetricPoint] = deque()
        self._costs: deque[MetricPoint] = deque()
        self._iterations: deque[MetricPoint] = deque()
        self._successes: deque[MetricPoint] = deque()
        self._failures: deque[MetricPoint] = deque()
        self._snapshots: deque[AgentMetricsSnapshot] = deque(maxlen=1000)

    def _trim(self) -> float:
        """Remove data points older than the window and return cutoff time."""
        cutoff = time.time() - self.window_seconds
        for buf in (self._latencies, self._token_usage, self._costs, self._iterations,
                     self._successes, self._failures):
            while buf and buf[0].timestamp < cutoff:
                buf.popleft()
        return cutoff

    def record_execution(self, snapshot: AgentMetricsSnapshot) -> None:
        """Record a full agent execution snapshot."""
        now = time.time()
        self._snapshots.append(snapshot)
        self._latencies.append(MetricPoint(now, snapshot.latency_ms, {"agent": snapshot.agent_type}))
        self._token_usage.append(MetricPoint(now, float(snapshot.token_count), {"agent": snapshot.agent_type}))
        self._costs.append(MetricPoint(now, snapshot.cost_usd, {"agent": snapshot.agent_type}))
        self._iterations.append(MetricPoint(now, float(snapshot.iterations), {"agent": snapshot.agent_type}))
        if snapshot.success:
            self._successes.append(MetricPoint(now, 1.0, {"agent": snapshot.agent_type}))
        else:
            self._failures.append(MetricPoint(now, 1.0, {"agent": snapshot.agent_type}))

    def record_latency(self, agent_type: str, latency_ms: float) -> None:
        self._latencies.append(MetricPoint(time.time(), latency_ms, {"agent": agent_type}))

    def record_tokens(self, agent_type: str, count: int) -> None:
        self._token_usage.append(MetricPoint(time.time(), float(count), {"agent": agent_type}))

    def record_cost(self, agent_type: str, cost_usd: float) -> None:
        self._costs.append(MetricPoint(time.time(), cost_usd, {"agent": agent_type}))

    def record_iteration(self, agent_type: str) -> None:
        self._iterations.append(MetricPoint(time.time(), 1.0, {"agent": agent_type}))

    def record_success(self, agent_type: str) -> None:
        self._successes.append(MetricPoint(time.time(), 1.0, {"agent": agent_type}))

    def record_failure(self, agent_type: str, error: str | None = None) -> None:
        self._failures.append(MetricPoint(time.time(), 1.0, {"agent": agent_type, "error": error or ""}))

    def get_latency_percentiles(self, agent_type: str | None = None) -> dict[str, float]:
        """Get p50, p95, p99 latency in ms."""
        self._trim()
        vals = [p.value for p in self._latencies if not agent_type or p.labels.get("agent") == agent_type]
        if not vals:
            return {"p50": 0, "p95": 0, "p99": 0}
        vals.sort()
        return {
            "p50": vals[len(vals) * 50 // 100],
            "p95": vals[len(vals) * 95 // 100],
            "p99": vals[len(vals) * 99 // 100],
        }

    def get_average_cost(self, agent_type: str | None = None) -> float:
        self._trim()
        vals = [p.value for p in self._costs if not agent_type or p.labels.get("agent") == agent_type]
        return sum(vals) / len(vals) if vals else 0.0

    def get_total_cost(self) -> float:
        self._trim()
        return sum(p.value for p in self._costs)

    def get_success_rate(self, agent_type: str | None = None) -> float:
        self._trim()
        successes = sum(1 for p in self._successes if not agent_type or p.labels.get("agent") == agent_type)
        failures = sum(1 for p in self._failures if not agent_type or p.labels.get("agent") == agent_type)
        total = successes + failures
        return successes / total if total > 0 else 1.0

    def get_total_iterations(self, agent_type: str | None = None) -> int:
        self._trim()
        return int(sum(p.value for p in self._iterations if not agent_type or p.labels.get("agent") == agent_type))

    def get_throughput(self) -> float:
        """Requests per second over the current window."""
        self._trim()
        return len(self._snapshots) / self.window_seconds if self.window_seconds > 0 else 0.0

    def get_too_many_loops_detected(self, threshold: int = 20) -> list[AgentMetricsSnapshot]:
        """Detect agent executions that exceeded the loop threshold."""
        return [s for s in self._snapshots if s.iterations > threshold]

    def summary(self, agent_type: str | None = None) -> dict[str, Any]:
        """Return a full metrics summary dict (for API / dashboard)."""
        return {
            "latency_ms": self.get_latency_percentiles(agent_type),
            "avg_cost_usd": self.get_average_cost(agent_type),
            "total_cost_usd": self.get_total_cost(),
            "success_rate": self.get_success_rate(agent_type),
            "total_iterations": self.get_total_iterations(agent_type),
            "throughput_rps": self.get_throughput(),
            "total_snapshots": len(self._snapshots),
            "excessive_loops": len(self.get_too_many_loops_detected()),
        }

    @property
    def total_executions(self) -> int:
        return len(self._snapshots)
