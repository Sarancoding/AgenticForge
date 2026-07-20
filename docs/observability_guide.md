# 🔭 NexusCore Observability Guide

## Overview

NexusCore Enterprise provides production-grade observability across five dimensions:

| Dimension | Tool | Purpose |
|---|---|---|
| **Tracing** | LangSmith / Arize Phoenix | Distributed trace spans through agent → tool → LLM calls |
| **Metrics** | Built-in collector | Latency percentiles, token usage, cost, throughput |
| **Alerting** | Rule-based engine | Automatic detection of loops, failures, cost spikes, latency |
| **Canary Testing** | Traffic-split framework | Safe rollout of new models/configs with auto-rollback |
| **Rollback** | Config snapshots | One-click restore to any previous known-good state |

---

## 1. Distributed Tracing

### LangSmith Setup

```bash
export LANGSMITH_API_KEY="lsv2_..."
export LANGSMITH_PROJECT="nexuscore-enterprise"
```

The `TracerManager` auto-detects LangSmith from the environment:

```python
from src.observability import TracerManager
tracer = TracerManager(service_name="nexuscore")

with tracer.trace("agent.react", span_type="chain", inputs={"task": task}) as span:
    result = run_agent(task)
    span.set_output({"result": result})
    span.set_usage(input_tokens=50, output_tokens=200, total_tokens=250)
```

### Arize Phoenix Setup

```bash
export PHOENIX_COLLECTOR_ENDPOINT="http://localhost:6006/v1/traces"
```

Phoenix uses OpenTelemetry under the hood, automatically instrumenting
FastAPI endpoints and LLM calls.

### Span Hierarchy

```
nexuscore.request (chain)
├── agent.react (chain)
│   ├── llm.call (llm) — token counts, cost
│   ├── tool.search_web (tool) — latency, success/failure
│   └── llm.call (llm) — reflection step
├── memory.recall (retriever) — similarity scores
└── workflow.debate (chain)
    ├── agent.proposer_1 (llm)
    ├── agent.proposer_2 (llm)
    └── agent.critic (llm)
```

---

## 2. Metrics Collection

The `MetricsCollector` maintains rolling windows (configurable, default 5 min)
and calculates real-time percentiles.

```python
from src.observability import MetricsCollector
from src.observability.metrics import AgentMetricsSnapshot

metrics = MetricsCollector(window_seconds=300)
metrics.record_execution(AgentMetricsSnapshot(
    agent_type="react",
    latency_ms=145.2,
    token_count=350,
    cost_usd=0.0025,
    iterations=3,
    success=True,
))

# Get summary
summary = metrics.summary()
# {
#   "latency_ms": {"p50": 120, "p95": 450, "p99": 890},
#   "avg_cost_usd": 0.0032,
#   "success_rate": 0.95,
#   "throughput_rps": 2.3,
#   ...
# }
```

### REST API Endpoint

```bash
curl http://localhost:8000/api/observability/metrics
curl http://localhost:8000/api/observability/metrics?agent_type=react
```

---

## 3. Alerting

### Built-in Alert Rules

| Rule | Severity | Condition |
|---|---|---|
| `excessive_loops` | WARNING | Any agent exceeds 20 iterations |
| `high_failure_rate` | CRITICAL | Success rate < 80% |
| `high_latency` | WARNING | p95 > 10 seconds |
| `cost_spike` | INFO | Total cost > $1.00 in window |
| `no_heartbeat` | CRITICAL | Zero executions detected |

### Custom Rules

```python
from src.observability import AlertEngine, AlertRule, AlertSeverity

alerts = AlertEngine()
alerts.register_rule(AlertRule(
    name="budget_exceeded",
    description="Daily budget exceeded",
    severity=AlertSeverity.CRITICAL,
    check_fn=lambda m: m.get("total_cost_usd", 0) > 5.0,
    message_template="Daily budget exceeded: ${total_cost_usd:.2f}",
))
```

### REST API

```bash
curl http://localhost:8000/api/observability/alerts
curl -X POST http://localhost:8000/api/observability/alerts/acknowledge?index=0
```

---

## 4. Canary Testing

Canary testing allows safe rollouts by routing a percentage of traffic
to a candidate configuration and comparing metrics.

```python
from src.observability import CanaryTester

canary = CanaryTester(baseline_fn=current_model)
canary.update_baseline_metrics({"latency_ms": 100.0, "failure_rate": 0.05})

# Start canary — 10% of traffic to new model
canary.start_canary("gpt-4o-mini-v2", candidate_fn=new_model, traffic_percent=10)

# After observation period, evaluate
result = canary.evaluate_and_maybe_promote("gpt-4o-mini-v2")
if result.passed:
    canary.promote("gpt-4o-mini-v2")  # Full rollout
else:
    canary.rollback("gpt-4o-mini-v2")  # Auto-rollback
```

---

## 5. Rollback Management

Every configuration change is snapshotted for instant rollback.

```python
from src.observability import RollbackManager

rb = RollbackManager()

# Before deployment
snap_id = rb.snapshot({"model": "gpt-4o", "budget": 0.10}, "Pre-deployment v2.0")

# If issues detected
config = rb.rollback_to(snap_id)  # One-click restore

# Full audit trail
history = rb.get_rollback_history()
```
