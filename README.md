# ⚡ NexusCore — The Unified Agentic Orchestration Platform

> **Intelligence that routes. Agents that collaborate. Systems that learn.**

NexusCore is a production-ready, modular agentic platform that unifies eight distinct agent archetypes into one cohesive runtime. It provides cost-aware routing, hybrid memory, human-in-the-loop safety, multi-agent debate, event-driven automation, and self-reflective improvement — all served through a clean FastAPI backend and an interactive Streamlit dashboard.

---

## ✨ Features Overview

| Capability | Business Value |
|---|---|
| **ReAct Planning Agent** | Reliable task decomposition with self-critique and graceful degradation. Never infinite loops. |
| **Multi-Tool Orchestrator** | Dynamic tool registration, capability routing, and parallel execution with conflict resolution. |
| **Memory-Enabled Conversational Agent** | Hybrid short-term + long-term vector recall for context-aware conversations across sessions. |
| **Human-in-the-Loop (HITL) Approval** | Uncertainty detection pauses workflows, requests human input, resumes with full audit trail. |
| **Cost-Aware Agent Router** | Token-budgeted model selection routes simple tasks to cheap models, complex tasks to powerful ones. |
| **Event-Triggered Automation** | Webhook/queue listeners with idempotent execution, dead-letter handling, and exponential backoff retry. |
| **Multi-Agent Debate System** | Swarm of proposing agents, a critic evaluator, voting/consensus aggregation, and synthesis. |
| **Self-Reflective Agent with Auto-Eval** | LLM-as-judge evaluation → critique → constrained regeneration → improvement metric logging. |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ ReAct    │  │ Debate   │  │ Self-    │  │ Event-     │ │
│  │ Agent    │  │ System   │  │ Reflective│  │ Triggered  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘ │
│       └──────────────┴─────────────┴──────────────┘        │
│                        │                                    │
│              ┌─────────▼──────────┐                         │
│              │   Cost-Aware Router │                         │
│              └─────────┬──────────┘                         │
│                        │                                    │
│         ┌──────────────┼──────────────┐                     │
│  ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼──────┐              │
│  │ Tool        │ │ Hybrid    │ │ HITL       │              │
│  │ Orchestrator│ │ Memory    │ │ Workflow   │              │
│  └─────────────┘ └───────────┘ └────────────┘              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐    ┌──────────────────┐
│ Streamlit UI     │    │ REST API Clients │
│ (Testing Dashboard)  │ (cURL, SDK, etc.) │
└──────────────────┘    └──────────────────┘
```

**Data Flow:**
1. **Ingress**: User request enters via REST API or Streamlit UI.
2. **Routing**: `CostAwareRouter` selects the optimal agent and model based on task complexity and token budget.
3. **Execution**: The chosen agent executes — calling tools, consulting memory, or pausing for human approval as needed.
4. **Orchestration**: `ToolOrchestrator` manages parallel tool calls with conflict resolution.
5. **Memory**: `HybridMemory` logs the interaction into short-term buffer and long-term vector store.
6. **Reflection**: Optional self-evaluation loop improves output quality.
7. **Response**: Final output is returned with full cost and audit metadata.

---

## 🎯 Use Cases

### 1. **AI-Powered Customer Support Triage**
A support ticket enters the system. The Cost-Aware Router classifies it as "low complexity" and routes it to a lightweight model with tool access to the knowledge base. If the confidence score is low, the HITL workflow pauses for a human agent to review before the response is sent.

### 2. **Multi-Agent Code Review Pipeline**
A pull request is submitted. Three debater agents propose code improvements. A critic agent evaluates each for security, performance, and readability. The aggregator synthesizes a final review. The Self-Reflective Agent then evaluates its own critique quality and logs improvement metrics.

### 3. **Autonomous Incident Response**
A monitoring webhook fires. The Event-Triggered Agent picks it up, fetches logs via the tool orchestrator, analyzes root cause using the ReAct loop, and — if the severity is above threshold — pauses for human approval before executing a remediation workflow.

---

## 🛡️ Key Benefits

- **🔒 Safety-First**: HITL pause/resume with full audit trails prevents unintended actions.
- **💰 Cost-Efficient**: Token-aware routing saves up to 60% on LLM costs by matching task complexity to the right model.
- **⚡ Reliable**: Dead-letter handling, exponential backoff retries, and max-iteration hard stops prevent runaway agents.
- **🧩 Modular**: Each agent archetype is a self-contained component. Add, remove, or replace without touching the core.
- **📊 Observable**: Every decision, token spend, and reflection metric is logged for monitoring and debugging.

---

## 🚀 Quick Start

```bash
# Prerequisites: Python 3.10+, pip

# Clone & enter
git clone https://github.com/Sarancoding/AgenticForge.git
cd AgenticForge

# Set up environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your OpenAI/Anthropic API key

# Start backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start dashboard
streamlit run ui/app.py
```

---

## 📚 Documentation

| Document | Description |
|---|---|
| [Technical Overview](docs/overview.md) | System architecture, agent interactions, and design decisions |
| [Installation Guide](INSTALL.md) | Step-by-step setup, configuration, and deployment |

---

## 📄 License

MIT © 2026 Sarancoding
