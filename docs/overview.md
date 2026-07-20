# 🏗️ NexusCore — Technical Architecture Overview

## System Architecture

NexusCore is built on a **modular, event-driven microkernel architecture**. Each agent archetype is an independent module that communicates through a central `CostAwareRouter`. The system uses **LangGraph** for state graph-based workflow management, **FastAPI** for the REST API layer, and a **pluggable vector store interface** for memory.

---

## Core Components

### 1. Cost-Aware Router (`agents/router.py`)

The `CostAwareRouter` is the brain of the platform. Every request passes through it.

**Decision Logic:**
1. **Task Classification**: Analyzes the prompt to estimate complexity (token count, required tools, ambiguity).
2. **Model Selection**: Maps complexity to a cost tier:
   - *Tier 1 (Low)*: `gpt-4o-mini` — Simple Q&A, classification
   - *Tier 2 (Medium)*: `gpt-4o` — Tool use, multi-step reasoning
   - *Tier 3 (High)*: `o1-mini` — Complex debate, code generation
3. **Agent Selection**: Routes to the appropriate agent based on task type.
4. **Budget Enforcement**: If estimated cost exceeds the task budget, either degrades the model or rejects with a budget advisory.

> **Why this matters**: Simple queries don't need GPT-4. The router saves 40-60% on LLM costs by matching complexity to capability.

### 2. ReAct Planning Agent (`agents/react_agent.py`)

Implements the **Observe → Think → Act → Reflect** loop.

| Phase | Description |
|---|---|
| **Observe** | Parse input, gather context from memory and tools |
| **Think** | Generate reasoning about what action to take |
| **Act** | Execute a tool call or produce a response |
| **Reflect** | Self-critique the action; regenerate if improvement is needed |

**Safeguards:**
- Max iteration limit (default: 15) — hard stop prevents infinite loops.
- Graceful degradation — if a tool fails, the agent logs the error and continues with an alternative approach.
- Self-critique threshold — if confidence drops below 0.3, triggers HITL pause.

### 3. Multi-Tool Orchestrator (`tools/orchestrator.py`)

A dynamic tool registry that supports:

- **Registration**: Tools register by name, capability tags, and permission scope.
- **Routing**: The orchestrator matches tasks to tools by capability tags.
- **Parallel Execution**: Independent tools run concurrently via `asyncio.gather`.
- **Conflict Resolution**: If two tools claim the same capability, the one with the highest confidence score wins.

### 4. Hybrid Memory (`memory/memory_manager.py`)

Two-tier memory architecture:

| Tier | Storage | Recall | Use Case |
|---|---|---|---|
| **Short-Term Buffer** | In-memory deque (last N turns) | FIFO sliding window | Recent conversation context |
| **Long-Term Vector Recall** | ChromaDB / any Vector DB | Semantic similarity search | Cross-session knowledge |

**Relevance Scoring**: Each memory item is scored by:
- Recency (time decay)
- Relevance (cosine similarity to current query)
- Importance (explicitly marked by agent)

### 5. Human-in-the-Loop Workflow (`workflows/hitl_workflow.py`)

A LangGraph state machine with five states:

```
Input → Analyze → [Confidence > Threshold?]
    ├── Yes → Execute → Output
    └── No  → Pause → WaitForHuman → ValidateInput → Resume → Output
```

**Audit Trail**: Every pause, human input, and resumption is logged with timestamps, user ID, and the exact context snapshot at pause time.

### 6. Multi-Agent Debate System (`agents/debate_agent.py`)

Swarm orchestration pattern:

1. **Proposers** (N agents): Each generates a solution independently.
2. **Critic**: Evaluates each proposal against criteria (correctness, efficiency, safety).
3. **Voting**: Weighted consensus based on critic scores.
4. **Aggregator**: Synthesizes the final output from the highest-scored proposals.

### 7. Self-Reflective Agent (`agents/self_reflective_agent.py`)

Meta-cognition loop:

1. **Execute**: Generate initial output.
2. **Evaluate**: Use an LLM-as-judge to score the output (1-10) with critique.
3. **Critique Reasoning**: Analyze the critique to identify specific weaknesses.
4. **Regenerate**: Produce improved output with the critique as constraints.
5. **Log Metrics**: Track score improvement across iterations.

### 8. Event-Triggered Automation Agent (`agents/event_agent.py`)

Listener-based architecture:

- **Triggers**: Webhooks, Redis pub/sub, message queues (RabbitMQ).
- **Idempotency**: Each event carries a unique ID; duplicate events are ignored.
- **Execution**: The workflow is launched with full context from the event payload.
- **Retry**: Exponential backoff (1s, 2s, 4s, 8s…) with configurable max retries.
- **Dead-Letter**: Events that exhaust retries are moved to a dead-letter queue for manual inspection.

---

## Agent Interaction Flow

```
┌─────────┐     ┌──────────┐     ┌────────────┐     ┌───────────┐
│  User   │────▶│  Router  │────▶│   Agent    │────▶│  Tools    │
│ Request │     │          │     │  (ReAct/   │     │           │
└─────────┘     │          │     │   Debate/  │     └───────────┘
                │          │     │   Event)   │          │
                └──────────┘     └─────┬──────┘          │
                                       │                 │
                                ┌──────▼──────┐   ┌──────▼──────┐
                                │   Memory    │   │    HITL     │
                                │  (Short +   │   │   Pause?    │
                                │   Long)     │   └─────────────┘
                                └─────────────┘
                                       │
                                ┌──────▼──────┐
                                │  Self-      │
                                │  Reflective │
                                │  Loop?      │
                                └──────┬──────┘
                                       │
                                ┌──────▼──────┐
                                │   Response  │
                                │  (with cost │
                                │   & audit)  │
                                └─────────────┘
```

---

## Safety & Compliance

| Mechanism | Description |
|---|---|
| **HITL Pause** | Workflow pauses when confidence < threshold; human reviews and approves/rejects |
| **Audit Trails** | Every action logged with agent ID, timestamp, context snapshot, and decision rationale |
| **Permission Scoping** | Tools are registered with permission levels; sensitive tools require HITL approval |
| **Budget Limits** | Per-task token budgets prevent runaway costs |
| **Max Iterations** | Hard stop on ReAct loops prevents infinite cycles |
| **Dead-Letter Queue** | Failed events are captured for manual review |

---

## Cost Management

The `CostAwareRouter` uses a tiered decision matrix:

| Complexity | Estimated Tokens | Model | Cost/Task |
|---|---|---|---|
| Low | < 500 | `gpt-4o-mini` | ~$0.00015 |
| Medium | 500-2000 | `gpt-4o` | ~$0.01 |
| High | 2000-8000 | `o1-mini` | ~$0.02 |
| Very High | 8000+ | `o1-preview` | ~$0.05 |

**Early Exit**: If the agent reaches high confidence (>0.9) before max iterations, it exits early, saving remaining budget.

---

## Scalability

- **Parallel Execution**: The `ToolOrchestrator` uses `asyncio.gather` for concurrent tool calls.
- **Event-Driven**: The `EventAgent` uses async listeners and can scale horizontally behind a message queue.
- **Stateless Backend**: FastAPI is stateless; memory persistence moves to the vector store.
- **Horizontal Scaling**: Multiple backend instances behind a load balancer, sharing the same vector store and message queue.
