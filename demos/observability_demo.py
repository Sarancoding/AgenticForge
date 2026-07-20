#!/usr/bin/env python3
"""
NexusCore Observability Demo — demonstrates tracing, metrics, alerts,
canary testing, and rollback in action.

Usage:
    python demos/observability_demo.py
"""

from __future__ import annotations

import json
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.observability import (
    TracerManager,
    MetricsCollector,
    AlertEngine,
    CanaryTester,
    RollbackManager,
    AlertSeverity,
    AlertRule,
)


def demonstrate_tracing():
    """Show LangSmith/Phoenix-style tracing."""
    print("\n" + "=" * 60)
    print("1. DISTRIBUTED TRACING")
    print("=" * 60)

    tracer = TracerManager(service_name="demo")
    print(f"   Provider: {tracer.provider}")

    with tracer.trace("demo.workflow", span_type="chain",
                       inputs={"task": "Say hello in 5 languages"}) as span:
        print("   ▶ Span started: demo.workflow")
        time.sleep(0.05)
        span.set_output({"result": "Hello, Hola, Bonjour, Ciao, Hallo"})
        span.set_usage(input_tokens=10, output_tokens=15, total_tokens=25)
        print("   ✓ Span completed with output")

    print("   ✓ Tracing demo complete")


def demonstrate_metrics_collection():
    """Show metrics collection and percentiles."""
    print("\n" + "=" * 60)
    print("2. METRICS COLLECTION")
    print("=" * 60)

    metrics = MetricsCollector(window_seconds=60)

    # Simulate 50 agent executions with varying latencies
    from src.observability.metrics import AgentMetricsSnapshot
    for i in range(50):
        latency = 50 + (i * 3) % 200  # 50ms - 250ms
        metrics.record_execution(AgentMetricsSnapshot(
            agent_type="react",
            latency_ms=float(latency),
            token_count=100 + i,
            cost_usd=0.001 + (i * 0.0001),
            iterations=(i % 5) + 1,
            success=i % 10 != 0,  # 10% failure rate
            error="Timeout" if i % 10 == 0 else None,
        ))

    summary = metrics.summary()
    print(f"   Total executions: {summary['total_snapshots']}")
    print(f"   Success rate:      {summary['success_rate']:.1%}")
    print(f"   p50 latency:       {summary['latency_ms']['p50']:.0f} ms")
    print(f"   p95 latency:       {summary['latency_ms']['p95']:.0f} ms")
    print(f"   p99 latency:       {summary['latency_ms']['p99']:.0f} ms")
    print(f"   Avg cost/task:     ${summary['avg_cost_usd']:.5f}")
    print(f"   Total cost:        ${summary['total_cost_usd']:.4f}")
    print(f"   Throughput:        {summary['throughput_rps']:.2f} req/s")
    print(f"   Excessive loops:   {summary['excessive_loops']}")
    print("   ✓ Metrics collection demo complete")

    return metrics


def demonstrate_alerting(metrics: MetricsCollector):
    """Show alert rule evaluation."""
    print("\n" + "=" * 60)
    print("3. ALERTING ENGINE")
    print("=" * 60)

    alerts = AlertEngine()

    # Register a custom rule
    alerts.register_rule(AlertRule(
        name="demo_high_latency",
        description="Alert when p50 > 200ms",
        severity=AlertSeverity.WARNING,
        check_fn=lambda m: m.get("latency_ms", {}).get("p50", 0) > 200,
        message_template="High latency detected: p50={latency_ms[p50]:.0f}ms",
    ))

    # Evaluate
    summary = metrics.summary()
    fired = alerts.evaluate(summary)

    print(f"   Built-in rules: 5")
    print(f"   Custom rules:   1")
    print(f"   Alerts fired:   {len(fired)}")
    for alert in fired:
        print(f"   ⚠ [{alert.severity.value.upper()}] {alert.rule_name}: {alert.message[:80]}")

    if not fired:
        print("   ✓ No alerts — all metrics within thresholds")

    print("   ✓ Alerting demo complete")
    return alerts


def demonstrate_canary_testing():
    """Show canary testing workflow."""
    print("\n" + "=" * 60)
    print("4. CANARY TESTING")
    print("=" * 60)

    def baseline(task: str, **kw) -> str:
        return f"[Baseline response to: {task[:40]}]"

    canary = CanaryTester(baseline_fn=baseline, observation_period=10)
    canary.update_baseline_metrics({"latency_ms": 100.0, "failure_rate": 0.05})

    # Start a canary
    canary.start_canary("gpt-4o-mini-v2", lambda t: f"[v2: {t[:40]}]", 10)
    print("   ▶ Canary started: gpt-4o-mini-v2 (10% traffic)")

    # Simulate routing (only using baseline in this demo)
    result, name, is_canary = canary.execute("Test task")
    print(f"   ▶ Routed to: {name} (canary={is_canary})")

    print("   ✓ Canary testing demo complete")
    return canary


def demonstrate_rollback():
    """Show config snapshots and rollback."""
    print("\n" + "=" * 60)
    print("5. ROLLBACK MANAGEMENT")
    print("=" * 60)

    rb = RollbackManager()

    # Take snapshot
    s1 = rb.snapshot({"model": "gpt-4o", "budget": 0.10}, "Deployment v1.0")
    print(f"   ▶ Snapshot 1: {s1}")

    # Update and snapshot again
    s2 = rb.snapshot({"model": "gpt-4o-mini", "budget": 0.05}, "Deployment v1.1 (cheaper)")
    print(f"   ▶ Snapshot 2: {s2}")

    # List snapshots
    for s in rb.list_snapshots():
        print(f"   📸 {s['id']}: {s['description']} {'(current)' if s['is_current'] else ''}")

    # Rollback
    config = rb.rollback_to(s1)
    print(f"   ▶ Rolled back to {s1}: model={config['model']}")
    print(f"   ▶ Rollback history: {len(rb.get_rollback_history())} event(s)")

    print("   ✓ Rollback demo complete")


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║     NexusCore Observability Demo Suite          ║")
    print("╚══════════════════════════════════════════════════╝")

    demonstrate_tracing()
    metrics = demonstrate_metrics_collection()
    demonstrate_alerting(metrics)
    demonstrate_canary_testing()
    demonstrate_rollback()

    print("\n" + "=" * 60)
    print("✅ All observability demos completed successfully!")
    print("=" * 60)
