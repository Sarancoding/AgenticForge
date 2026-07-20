# ⚡ NexusCore Enterprise — The Global Agentic Orchestration Platform

> **Deploy Intelligent Agent Teams at Enterprise Scale.**
> *Cost-aware routing · Full observability · Canary rollouts · One-click rollback.*

[![Version](https://img.shields.io/badge/version-0.2.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.10+-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Enterprise](https://img.shields.io/badge/enterprise-ready-gold)]()

---

## 🌍 For Global Business Operations

NexusCore Enterprise is a **production-grade agentic orchestration platform** designed for organizations that need reliable, observable, and cost-efficient AI agent deployments. It unifies **10 agent archetypes** — from ReAct planning to Crew-style hierarchical teams — into one cohesive runtime with enterprise observability.

### Executive Summary

| For | NexusCore Delivers |
|---|---|
| **CTO / VP Engineering** | Production-ready agent infrastructure with observability, canary testing, and rollback |
| **AI/ML Teams** | 10 pluggable agent patterns with cost-aware routing (up to 87% savings) |
| **DevOps / SRE** | LangSmith/Phoenix tracing, latency/cost metrics, and alerting on loops/failures |
| **Business Stakeholders** | Measurable ROI: lower costs, faster deployments, safe rollouts |

---

## ✨ 10 Agent Archetypes

| # | Agent | Pattern | Business Value |
|---|---|---|---|
| 1 | **ReAct Planning** | Observe → Think → Act → Reflect | Reliable multi-step reasoning with hard stops |
| 2 | **Multi-Agent Debate** | Proposers → Critic → Vote → Aggregate | Higher-quality decisions via swarm intelligence |
| 3 | **Self-Reflective** | Execute → Evaluate → Improve | Quality-critical output with auto-improvement |
| 4 | **Event-Triggered** | Listen → Process → Retry → DLQ | Autonomous workflow automation |
| 5 | **Cost-Aware Router** | Complexity → Model → Budget | **60-87% cost reduction** |
| 6 | **👥 Crew Agent** | Manager → Specialists → Synthesize | Hierarchical team-based research & analysis |
| 7 | **🔄 Workflow Agent** | Chain · Trio · Reflect patterns | AutoGen-style multi-step content creation |
| 8 | **🛂 HITL Approval** | Pause → Human Input → Resume | Safety gate for sensitive operations |
| 9 | **🧠 Hybrid Memory** | Short-term buffer + Vector recall | Cross-session context awareness |
| 10 | **🔧 Tool Orchestrator** | Register → Route → Execute | Extensible plugin system |

---

## 🔭 Enterprise Observability Stack

| Layer | Technology | What You Get |
|---|---|---|
| **Tracing** | LangSmith / Arize Phoenix | Distributed traces through agent → tool → LLM calls |
| **Metrics** | Built-in collector (Prometheus-style) | p50/p95/p99 latency, token usage, cost, throughput |
| **Alerting** | Rule-based engine | 5 built-in rules + custom rules for loops/failures/cost |
| **Canary Testing** | Traffic-split framework | Safe rollouts with auto-rollback on regression |
| **Rollback** | Config snapshots | One-click restore to any previous known-good state |

```bash
# Real-time metrics
curl http://localhost:8000/api/observability/metrics

# Active alerts
curl http://localhost:8000/api/observability/alerts

# Rollback to any snapshot
curl -X POST http://localhost:8000/api/observability/rollback/to/SNAPSHOT_ID
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Horizontally Scalable)           │
│                                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │  ReAct  │ │  Debate │ │  Self-  │ │  Crew   │ │ Workflow│        │
│  │  Agent  │ │  System │ │Reflective│ │  Agent  │ │ Agent   │        │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘        │
│       └───────────┴──────────┴───────────┴───────────┘               │
│                        │                                             │
│              ┌─────────▼──────────┐                                   │
│              │   Cost-Aware Router │ ← Token budget enforcement       │
│              └─────────┬──────────┘                                   │
│                        │                                             │
│    ┌───────────┬───────┴───────┬───────────┐                        │
│ ┌──▼─────┐ ┌──▼──────┐ ┌──────▼─────┐ ┌──▼──────────┐              │
│ │  Tool  │ │ Hybrid  │ │   HITL     │ │Observability │              │
│ │Orchestr│ │ Memory  │ │  Workflow  │ │   Stack     │              │
│ └────────┘ └─────────┘ └────────────┘ └─────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 5-Minute Quick Start

```bash
# 1. Clone
git clone https://github.com/Sarancoding/AgenticForge.git && cd AgenticForge

# 2. Install
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 3. Set API key
export OPENAI_API_KEY="sk-..."

# 4. Start backend
uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# 5. Start dashboard
streamlit run ui/app.py --server.port 8501 &

# 6. Verify
curl http://localhost:8000/health
```

---

## 📊 Cost Savings

| Scenario | Without Router | With Router | Savings |
|---|---|---|---|
| Customer Support Q&A | $0.015/task | $0.002/task | **87%** |
| Code Generation | $0.025/task | $0.008/task | **68%** |
| Research & Analysis | $0.030/task | $0.015/task | **50%** |

---

## 📚 Documentation

| Document | Format | Description |
|---|---|---|
| [Complete Setup Guide](GUIDE.md) | Markdown/PDF | Full enterprise operations guide (14 chapters) |
| [Installation Guide](INSTALL.md) | Markdown | Step-by-step setup & configuration |
| [Observability Guide](docs/observability_guide.md) | Markdown | Tracing, metrics, alerts, canary, rollback |
| [Enterprise Deployment](docs/enterprise_deployment.md) | Markdown | Docker, Kubernetes, scaling, security |
| [Benchmarks](docs/benchmarks.md) | Markdown | Performance, cost, and scalability benchmarks |
| [Technical Overview](docs/overview.md) | Markdown | System architecture & agent interactions |

### 📄 PDF Guide
Generate a professional PDF of the complete guide:
```bash
python scripts/generate_pdf.py
# Output: dist/NexusCore_Enterprise_Guide.pdf
```

---

## 🎯 Enterprise Use Cases

### 1. AI Customer Support Triage
Route tickets to the cheapest capable model. Escalate to humans on low confidence. Full audit trail.

### 2. Multi-Agent Code Review
Three debaters propose improvements. Critic evaluates. Aggregator synthesizes. Self-reflection auto-evaluates.

### 3. Crew-Based Research Reports
Manager decomposes complex research. Specialists execute in parallel. Manager synthesizes final report.

### 4. Autonomous Incident Response
Event-triggered agent picks up monitoring alerts. ReAct loop analyzes root cause. HITL gate for remediation.

---

## 🛡️ Enterprise Security & Compliance

- **HITL Approval**: Mandatory human gate for sensitive operations
- **Audit Trails**: Every state transition logged with timestamps
- **Tool Permissions**: Three levels (user/admin/system)
- **Config Snapshots**: Full version history with one-click rollback
- **Token Budgets**: Hard caps on per-task spending
- **Max Iterations**: Hard stops prevent runaway agents

---

## 📈 Observability in Action

| Dashboard Panel | What You See |
|---|---|
| **Latency** | p50, p95, p99 in real-time rolling window |
| **Cost** | Per-task average, total spend, budget remaining |
| **Reliability** | Success rate, throughput, excessive loop detection |
| **Alerts** | Active alerts with severity (🔴/🟡/🔵) and acknowledge |
| **Canary** | Active canary tests with pass/fail status |
| **Rollback** | Config snapshot history with one-click restore |

---

## 🏢 For Your Organization

NexusCore Enterprise is built for teams that need:
- **Reliability**: Canary testing prevents bad deployments from reaching production
- **Observability**: Full traceability from request → agent → tool → LLM
- **Cost Control**: Router saves 60-87% on LLM costs automatically
- **Safety**: HITL approval prevents unauthorized actions
- **Speed**: 5-minute setup from zero to running

---

## 📄 License

MIT © 2026 Sarancoding

---

*Built for global business operations. Deploy with confidence.*
