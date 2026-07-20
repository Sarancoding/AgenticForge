"""
NexusCore — FastAPI application entry point.

Initializes the agent router, exposes REST endpoints for all agent
archetypes, serves cost analytics, and provides health monitoring.
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
from src.memory.memory_manager import HybridMemory
from src.tools.orchestrator import ToolOrchestrator, Tool
from src.workflows.hitl_workflow import HITLWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("nexuscore")

# ─── Global Components ──────────────────────────────────────────────

router = CostAwareRouter(default_budget=0.10)
react_agent = ReActAgent()
debate_agent = DebateAgent()
reflective_agent = SelfReflectiveAgent()
event_agent = EventAgent()
memory = HybridMemory()
orchestrator = ToolOrchestrator()
workflows: dict[str, HITLWorkflow] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and clean up components."""
    # Startup
    logger.info("NexusCore starting up...")
    _register_default_tools()
    logger.info("ToolOrchestrator initialized with %d tools.", orchestrator.tool_count)
    yield
    # Shutdown
    logger.info("NexusCore shutting down.")


app = FastAPI(
    title="NexusCore API",
    description="Unified Agentic Orchestration Platform",
    version="0.1.0",
    lifespan=lifespan,
)


def _register_default_tools() -> None:
    """Register built-in tools for the demo."""
    import httpx

    def web_search(query: str) -> str:
        """Search the web for information. (Stub)"""
        return f"[Web search results for: {query}]"

    def calculator(expression: str) -> str:
        """Evaluate a mathematical expression."""
        try:
            return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307
        except Exception as e:
            return f"[Error: {e}]"

    def fetch_url(url: str) -> str:
        """Fetch the content of a URL."""
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


# ─── API Endpoints ──────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "service": "NexusCore",
        "version": "0.1.0",
        "endpoints": {
            "route": "/api/agents/route",
            "react": "/api/agents/react",
            "debate": "/api/agents/debate",
            "reflect": "/api/agents/reflect",
            "memory": "/api/memory",
            "hitl": "/api/workflows/hitl",
            "events": "/api/agents/events",
            "tools": "/api/tools",
            "health": "/health",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok", "tools_registered": orchestrator.tool_count}


# ─── Agent Endpoints ────────────────────────────────────────────────


@app.post("/api/agents/route")
async def route_task(req: RouteRequest):
    """Route a task to the optimal agent and model."""
    decision = router.route(task=req.task, agent_type=req.agent_type, budget=req.budget)
    return decision.model_dump()


@app.post("/api/agents/react")
async def run_react(req: ReActRequest):
    """Run the ReAct agent on a task."""
    result = react_agent.run(task=req.task, context=req.context)
    memory.add(
        content=f"User: {req.task}\nAssistant: {result.output}",
        importance=0.8,
        session_id="react_default",
    )
    return {
        "success": result.success,
        "output": result.output,
        "iterations": result.iterations,
        "error": result.error,
        "steps": [
            {"phase": s.phase.value, "thought": s.thought, "action": s.action, "confidence": s.confidence}
            for s in result.steps
        ],
    }


@app.post("/api/agents/debate")
async def run_debate(req: DebateRequest):
    """Run a multi-agent debate."""
    debate_agent.num_proposers = req.num_proposers
    result = debate_agent.debate(task=req.task)
    return {
        "consensus": result.consensus_output,
        "proposals": [
            {"agent_id": p.agent_id, "content": p.content, "score": p.critic_score, "votes": p.votes}
            for p in result.proposals
        ],
        "winner": result.winner.content if result.winner else None,
    }


@app.post("/api/agents/reflect")
async def run_reflection(req: ReflectRequest):
    """Run the self-reflective agent."""
    result = reflective_agent.reflect(task=req.task)
    return {
        "final_output": result.final_output,
        "improvement": result.improvement,
        "iterations": len(result.metrics),
        "metrics": [
            {"iteration": m.iteration, "score": m.score, "critique": m.critique}
            for m in result.metrics
        ],
    }


@app.post("/api/agents/events")
async def process_event(req: EventRequest):
    """Submit an event for the event agent to process."""
    event = event_agent.create_event(payload=req.payload)
    result = await event_agent.process_event(event)
    return {
        "event_id": result.event_id,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "processing_time": result.processing_time,
    }


# ─── Memory Endpoints ───────────────────────────────────────────────


@app.post("/api/memory/add")
async def add_memory(req: MemoryAddRequest):
    """Add an item to memory."""
    memory.add(content=req.content, importance=req.importance, session_id=req.session_id)
    return {"status": "ok"}


@app.post("/api/memory/query")
async def query_memory(req: MemoryQueryRequest):
    """Query memory with semantic search."""
    result = memory.search(query=req.query, top_k=req.top_k, session_id=req.session_id)
    return {
        "query": req.query,
        "results": [
            {"content": item.content, "score": result.scores[i] if i < len(result.scores) else 0.0}
            for i, item in enumerate(result.items)
        ],
    }


# ─── HITL Workflow Endpoints ────────────────────────────────────────


@app.post("/api/workflows/hitl/analyze")
async def hitl_analyze(req: HITLRequest):
    """Analyze a task and request human input if needed."""
    wf = HITLWorkflow()
    workflow_id = f"wf_{len(workflows) + 1}"
    workflows[workflow_id] = wf
    result = wf.run(task=req.task, agent_output=req.agent_output, confidence=req.confidence,
                    uncertainty_reason=req.uncertainty_reason)
    return {
        "workflow_id": workflow_id,
        "success": result.success,
        "output": result.output,
        "final_state": result.final_state,
        "needs_human_input": wf.current_state == "paused",
        "audit_trail": [{"timestamp": a.timestamp, "state": a.state, "action": a.action} for a in result.audit_trail],
    }


@app.post("/api/workflows/hitl/input")
async def hitl_input(req: HumanInputRequest):
    """Provide human input for a paused HITL workflow."""
    wf = workflows.get(req.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{req.workflow_id}' not found.")
    try:
        wf.provide_human_input(approved=req.approved, input_text=req.input_text)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "workflow_id": req.workflow_id,
        "final_state": wf.current_state,
        "audit_trail": [{"timestamp": a.timestamp, "state": a.state, "action": a.action} for a in wf.audit_trail],
    }


# ─── Tool Endpoints ─────────────────────────────────────────────────


@app.get("/api/tools")
async def list_tools():
    """List all registered tools."""
    return {"tools": orchestrator.list_tools(), "count": orchestrator.tool_count}


@app.post("/api/tools/execute")
async def execute_tool(name: str, **kwargs):
    """Execute a specific tool."""
    result = await orchestrator.execute_tool(name, **kwargs)
    return {"success": result.success, "output": result.output, "error": result.error}


# ─── Main Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
