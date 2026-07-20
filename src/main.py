"""
NexusCore Enterprise — FastAPI entry point with full observability,
extended agent patterns, canary testing, rollback, and alerting.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.agents.router import CostAwareRouter
from src.agents.react_agent import ReActAgent
from src.agents.debate_agent import DebateAgent
from src.agents.self_reflective_agent import SelfReflectiveAgent
from src.agents.event_agent import EventAgent
from src.agents.crew_agent import CrewAgent
from src.agents.workflow_agent import WorkflowAgent
from src.memory.memory_manager import HybridMemory
from src.tools.orchestrator import ToolOrchestrator, Tool
from src.workflows.hitl_workflow import HITLWorkflow
from src.observability import (
    TracerManager,
    MetricsCollector,
    AlertEngine,
    CanaryTester,
    RollbackManager,
    ObservabilityMiddleware,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("nexuscore")

# ─── Global Components ──────────────────────────────────────────────

router = CostAwareRouter(default_budget=0.10)
react_agent = ReActAgent()
debate_agent = DebateAgent()
reflective_agent = SelfReflectiveAgent()
event_agent = EventAgent()
crew_agent = CrewAgent()
workflow_agent = WorkflowAgent()
memory = HybridMemory()
orchestrator = ToolOrchestrator()
workflows: dict[str, HITLWorkflow] = {}

# Observability
tracer = TracerManager()
metrics = MetricsCollector(window_seconds=300)
alerts = AlertEngine()
canary = CanaryTester(baseline_fn=lambda t, **kw: f"[baseline: {t[:60]}]")
rollback = RollbackManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and clean up components."""
    logger.info("NexusCore Enterprise starting up...")
    _register_default_tools()

    # Take initial config snapshot
    rollback.snapshot({
        "tools": orchestrator.list_tools(),
        "agents": ["react", "debate", "reflective", "event", "crew", "workflow"],
        "router_budget": router.default_budget,
    }, description="Initial deployment")

    logger.info("System ready — provider=%s, tools=%d, agents=6",
                tracer.provider, orchestrator.tool_count)
    yield
    logger.info("NexusCore shutting down.")


app = FastAPI(
    title="NexusCore Enterprise API",
    description="Unified Agentic Orchestration Platform — Enterprise Edition with Observability",
    version="0.2.0",
    lifespan=lifespan,
)

# Register observability middleware
app.add_middleware(
    ObservabilityMiddleware,
    tracer=tracer,
    metrics=metrics,
    alerts=alerts,
)


def _register_default_tools() -> None:
    """Register built-in tools for the demo."""
    import httpx

    def web_search(query: str) -> str:
        return f"[Web search results for: {query}]"

    def calculator(expression: str) -> str:
        try:
            return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307
        except Exception as e:
            return f"[Error: {e}]"

    def fetch_url(url: str) -> str:
        try:
            response = httpx.get(url, timeout=10)
            return response.text[:2000]
        except Exception as e:
            return f"[Error fetching {url}: {e}]"

    orchestrator.register_tool(
        Tool(name="web_search", description="Search the web for information",
             capabilities=["search", "web"], fn=web_search)
    )
    orchestrator.register_tool(
        Tool(name="calculator", description="Evaluate mathematical expressions",
             capabilities=["math", "calculation"], fn=calculator)
    )
    orchestrator.register_tool(
        Tool(name="fetch_url", description="Fetch the content of a URL",
             capabilities=["web", "fetch"], fn=fetch_url)
    )


# ─── API Models ─────────────────────────────────────────────────────


class RouteRequest(BaseModel):
    task: str
    agent_type: str = "react"
    budget: float | None = None


class ReActRequest(BaseModel):
    task: str
    context: str = ""


class DebateRequest(BaseModel):
    task: str
    num_proposers: int = 3


class ReflectRequest(BaseModel):
    task: str


class WorkflowRequest(BaseModel):
    task: str
    pattern: str = "trio"


class CrewRequest(BaseModel):
    task: str
    members: list[str] | None = None


class MemoryAddRequest(BaseModel):
    content: str
    importance: float = 1.0
    session_id: str = "default"


class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    session_id: str | None = None


class HITLRequest(BaseModel):
    task: str
    agent_output: str
    confidence: float
    uncertainty_reason: str = ""


class HumanInputRequest(BaseModel):
    workflow_id: str
    approved: bool
    input_text: str | None = None


class EventRequest(BaseModel):
    payload: dict


# ─── Root & Health ──────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "service": "NexusCore Enterprise",
        "version": "0.2.0",
        "observability": tracer.provider,
        "endpoints": {
            "agents": "/api/agents/{type}",
            "observability": "/api/observability/metrics",
            "alerts": "/api/observability/alerts",
            "rollback": "/api/observability/rollback",
        },
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tools_registered": orchestrator.tool_count,
        "observability_provider": tracer.provider,
        "total_executions": metrics.total_executions,
    }


# ─── Agent Endpoints ────────────────────────────────────────────────


@app.post("/api/agents/route")
async def route_task(req: RouteRequest):
    decision = router.route(task=req.task, agent_type=req.agent_type, budget=req.budget)
    return decision.model_dump()


@app.post("/api/agents/react")
async def run_react(req: ReActRequest):
    result = react_agent.run(task=req.task, context=req.context)
    memory.add(content=f"User: {req.task}\nAssistant: {result.output}", importance=0.8, session_id="react_default")
    metrics.record_execution(__import__("src.observability.metrics", fromlist=["AgentMetricsSnapshot"]).AgentMetricsSnapshot(
        agent_type="react",
        latency_ms=100.0,
        token_count=len(result.output.split()),
        cost_usd=0.002,
        iterations=result.iterations,
        success=result.success,
        error=result.error,
    ))
    return {
        "success": result.success, "output": result.output,
        "iterations": result.iterations, "error": result.error,
        "steps": [{"phase": s.phase.value, "thought": s.thought, "action": s.action, "confidence": s.confidence}
                  for s in result.steps],
    }


@app.post("/api/agents/debate")
async def run_debate(req: DebateRequest):
    debate_agent.num_proposers = req.num_proposers
    result = debate_agent.debate(task=req.task)
    return {
        "consensus": result.consensus_output,
        "proposals": [{"agent_id": p.agent_id, "content": p.content, "score": p.critic_score, "votes": p.votes}
                      for p in result.proposals],
        "winner": result.winner.content if result.winner else None,
    }


@app.post("/api/agents/reflect")
async def run_reflection(req: ReflectRequest):
    result = reflective_agent.reflect(task=req.task)
    return {
        "final_output": result.final_output, "improvement": result.improvement,
        "iterations": len(result.metrics),
        "metrics": [{"iteration": m.iteration, "score": m.score, "critique": m.critique} for m in result.metrics],
    }


@app.post("/api/agents/crew")
async def run_crew(req: CrewRequest):
    if req.members:
        for mem in req.members:
            crew_agent.add_member(name=mem, role=mem, expertise=["general"])
    result = crew_agent.execute(task=req.task)
    return {
        "final_output": result.final_output,
        "manager_notes": result.manager_notes,
        "tasks": [{"agent": t.agent_name, "description": t.description, "result": t.result[:200]} for t in result.tasks],
    }


@app.post("/api/agents/workflow")
async def run_workflow(req: WorkflowRequest):
    result = workflow_agent.run(task=req.task, pattern=req.pattern)
    return {
        "final_output": result.final_output,
        "converged": result.converged,
        "total_tokens": result.total_tokens,
        "steps": [{"agent": s.agent_name, "output": s.output[:200]} for s in result.steps],
    }


@app.post("/api/agents/events")
async def process_event(req: EventRequest):
    event = event_agent.create_event(payload=req.payload)
    result = await event_agent.process_event(event)
    return {"event_id": result.event_id, "success": result.success, "output": result.output,
            "error": result.error, "processing_time": result.processing_time}


# ─── Observability Endpoints ────────────────────────────────────────


@app.get("/api/observability/metrics")
async def get_metrics(agent_type: str | None = None):
    """Get current metrics summary."""
    return metrics.summary(agent_type)


@app.get("/api/observability/alerts")
async def get_alerts():
    """Get recent and active alerts."""
    return {
        "active": [{"rule": a.rule_name, "severity": a.severity.value, "message": a.message, "timestamp": a.timestamp}
                   for a in alerts.get_active_alerts()],
        "recent": [{"rule": a.rule_name, "severity": a.severity.value, "message": a.message, "timestamp": a.timestamp}
                   for a in alerts.recent_alerts[-20:]],
        "rules": [{"name": r.name, "description": r.description, "severity": r.severity.value}
                  for r in alerts._rules.values()],
    }


@app.post("/api/observability/alerts/acknowledge")
async def acknowledge_alert(index: int):
    success = alerts.acknowledge(index)
    return {"success": success}


@app.get("/api/observability/rollback/snapshots")
async def list_snapshots():
    return {"snapshots": rollback.list_snapshots()}


@app.post("/api/observability/rollback/snapshot")
async def take_snapshot(description: str = ""):
    config = {
        "tools": orchestrator.list_tools(),
        "agents": ["react", "debate", "reflective", "event", "crew", "workflow"],
        "router_budget": router.default_budget,
    }
    snap_id = rollback.snapshot(config, description=description or "Manual snapshot")
    return {"snapshot_id": snap_id}


@app.post("/api/observability/rollback/to/{snapshot_id}")
async def rollback_to(snapshot_id: str):
    config = rollback.rollback_to(snapshot_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"restored_snapshot": snapshot_id, "config": config}


@app.get("/api/observability/canary")
async def get_canaries():
    return {"active": canary.active_canaries}


# ─── Memory Endpoints ───────────────────────────────────────────────


@app.post("/api/memory/add")
async def add_memory(req: MemoryAddRequest):
    memory.add(content=req.content, importance=req.importance, session_id=req.session_id)
    return {"status": "ok"}


@app.post("/api/memory/query")
async def query_memory(req: MemoryQueryRequest):
    result = memory.search(query=req.query, top_k=req.top_k, session_id=req.session_id)
    return {"query": req.query,
            "results": [{"content": item.content, "score": result.scores[i] if i < len(result.scores) else 0.0}
                        for i, item in enumerate(result.items)]}


# ─── HITL Workflow Endpoints ────────────────────────────────────────


@app.post("/api/workflows/hitl/analyze")
async def hitl_analyze(req: HITLRequest):
    wf = HITLWorkflow()
    workflow_id = f"wf_{len(workflows) + 1}"
    workflows[workflow_id] = wf
    result = wf.run(task=req.task, agent_output=req.agent_output, confidence=req.confidence,
                    uncertainty_reason=req.uncertainty_reason)
    return {"workflow_id": workflow_id, "success": result.success, "output": result.output,
            "final_state": result.final_state, "needs_human_input": wf.current_state == "paused",
            "audit_trail": [{"timestamp": a.timestamp, "state": a.state, "action": a.action} for a in result.audit_trail]}


@app.post("/api/workflows/hitl/input")
async def hitl_input(req: HumanInputRequest):
    wf = workflows.get(req.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{req.workflow_id}' not found.")
    try:
        wf.provide_human_input(approved=req.approved, input_text=req.input_text)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"workflow_id": req.workflow_id, "final_state": wf.current_state,
            "audit_trail": [{"timestamp": a.timestamp, "state": a.state, "action": a.action} for a in wf.audit_trail]}


# ─── Tool Endpoints ─────────────────────────────────────────────────


@app.get("/api/tools")
async def list_tools():
    return {"tools": orchestrator.list_tools(), "count": orchestrator.tool_count}


@app.post("/api/tools/execute")
async def execute_tool(name: str, **kwargs):
    result = await orchestrator.execute_tool(name, **kwargs)
    return {"success": result.success, "output": result.output, "error": result.error}


# ─── Main Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
