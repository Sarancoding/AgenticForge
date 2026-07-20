"""
NexusCore Enterprise — Streamlit Dashboard with full observability.

Interactive web UI to:
- Select and run all 10 agent archetypes
- View real-time ReAct/debate/crew/workflow logs
- Approve/reject HITL steps
- Explore cost analytics, latency metrics, and alert status
- View canary test results and rollback snapshots
"""

from __future__ import annotations

import os
import sys
from typing import Any

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.router import CostAwareRouter  # noqa: E402
from src.agents.react_agent import ReActAgent  # noqa: E402
from src.agents.debate_agent import DebateAgent  # noqa: E402
from src.agents.self_reflective_agent import SelfReflectiveAgent  # noqa: E402
from src.agents.crew_agent import CrewAgent  # noqa: E402
from src.agents.workflow_agent import WorkflowAgent  # noqa: E402
from src.memory.memory_manager import HybridMemory  # noqa: E402
from src.workflows.hitl_workflow import HITLWorkflow  # noqa: E402
from src.observability import (  # noqa: E402
    MetricsCollector, AlertEngine, CanaryTester, RollbackManager,
    TracerManager,
)

# ─── Page Config ───────────────────────────────────────────────────

st.set_page_config(
    page_title="NexusCore Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚡ NexusCore Enterprise Platform")
st.caption("Unified Agentic Orchestration — Production-Grade Observability")
st.markdown("---")

# ─── Initialize Components ─────────────────────────────────────────

if "router" not in st.session_state:
    st.session_state.router = CostAwareRouter()
if "react_agent" not in st.session_state:
    st.session_state.react_agent = ReActAgent()
if "debate_agent" not in st.session_state:
    st.session_state.debate_agent = DebateAgent()
if "reflective_agent" not in st.session_state:
    st.session_state.reflective_agent = SelfReflectiveAgent()
if "crew_agent" not in st.session_state:
    st.session_state.crew_agent = CrewAgent()
if "workflow_agent" not in st.session_state:
    st.session_state.workflow_agent = WorkflowAgent()
if "memory" not in st.session_state:
    st.session_state.memory = HybridMemory()
if "metrics" not in st.session_state:
    st.session_state.metrics = MetricsCollector()
if "alerts" not in st.session_state:
    st.session_state.alerts = AlertEngine()
if "canary" not in st.session_state:
    st.session_state.canary = CanaryTester(baseline_fn=lambda t, **kw: f"[baseline: {t[:60]}]")
if "rollback" not in st.session_state:
    st.session_state.rollback = RollbackManager()
if "workflow" not in st.session_state:
    st.session_state.workflow = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ─── Sidebar ───────────────────────────────────────────────────────

agent_options = [
    "ReAct Planning Agent",
    "Multi-Agent Debate",
    "Self-Reflective Agent",
    "👥 Crew Agent (Hierarchical)",
    "🔄 Workflow Agent (AutoGen)",
    "Memory Query",
    "HITL Approval Workflow",
    "Cost-Aware Router",
]

with st.sidebar:
    st.header("🧭 Agent Controls")
    agent_type = st.selectbox("Select Agent Archetype", options=agent_options, index=0)
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["⚙️ Config", "📊 Metrics", "🚨 Alerts"])

    with tab1:
        max_iterations = st.slider("Max Iterations", 1, 20, 5)
        st.session_state.react_agent.max_iterations = max_iterations
        budget = st.number_input("Token Budget ($)", 0.001, 1.0, 0.10, 0.01, format="%.3f")

        if st.button("📸 Take Config Snapshot", use_container_width=True):
            sid = st.session_state.rollback.snapshot({"budget": budget}, "Dashboard snapshot")
            st.success(f"Snapshot {sid} saved")

        snapshots = st.session_state.rollback.list_snapshots()
        if snapshots:
            snap_ids = [s["id"] for s in snapshots]
            selected = st.selectbox("Rollback to snapshot", snap_ids)
            if st.button("⏪ Rollback", use_container_width=True, type="primary"):
                config = st.session_state.rollback.rollback_to(selected)
                if config:
                    st.success(f"Rolled back to {selected}")

    with tab2:
        summary = st.session_state.metrics.summary()
        st.metric("Total Executions", summary["total_snapshots"])
        st.metric("Success Rate", f"{summary['success_rate']:.1%}")
        st.metric("p95 Latency", f"{summary['latency_ms']['p95']:.0f} ms")
        st.metric("Avg Cost", f"${summary['avg_cost_usd']:.5f}")
        st.metric("Total Cost", f"${summary['total_cost_usd']:.4f}")
        st.metric("Throughput", f"{summary['throughput_rps']:.2f} req/s")

    with tab3:
        active = st.session_state.alerts.get_active_alerts()
        if active:
            for a in active[-5:]:
                sev = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(a.severity.value, "⚪")
                st.warning(f"{sev} **{a.rule_name}**: {a.message[:80]}")
        else:
            st.success("✅ No active alerts")

    st.markdown("---")
    st.caption("NexusCore Enterprise v0.2.0")

# ─── Main Content ──────────────────────────────────────────────────

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("💬 Agent Playground")

    prompt = st.chat_input("Enter your task for the agent...")
    if prompt:
        st.session_state.task_input = prompt
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="⚡"):
            with st.status("Thinking...", expanded=True) as status:
                import time as _time
                start = _time.monotonic()

                if agent_type == "ReAct Planning Agent":
                    result = st.session_state.react_agent.run(task=prompt)
                    for i, step in enumerate(result.steps):
                        st.markdown(f"**Step {i + 1} — {step.phase.value.upper()}**")
                        if step.thought:
                            st.info(f"💭 {step.thought[:300]}")
                        if step.action:
                            st.text(f"⚡ Action: {step.action[:300]}")
                        st.caption(f"Confidence: {step.confidence:.2f}")
                        st.divider()
                    final = result.output
                    st.session_state.messages.append({"role": "assistant", "content": final})
                    st.markdown(final)

                elif agent_type == "Multi-Agent Debate":
                    st.session_state.debate_agent.num_proposers = 3
                    result = st.session_state.debate_agent.debate(task=prompt)
                    for p in result.proposals:
                        with st.expander(f"🤖 Debater #{p.agent_id} — Score: {p.critic_score:.1f}"):
                            st.markdown(p.content[:500])
                    st.success(f"**Consensus:** {result.consensus_output[:500]}")
                    if result.winner:
                        st.metric("Winner", f"Debater #{result.winner.agent_id}", f"Score: {result.winner.critic_score:.1f}")

                elif agent_type == "Self-Reflective Agent":
                    result = st.session_state.reflective_agent.reflect(task=prompt)
                    st.subheader("📈 Reflection Metrics")
                    for m in result.metrics:
                        st.markdown(f"**Iteration {m.iteration}** — Score: {m.score:.1f}/10")
                        st.text(f"Critique: {m.critique[:200]}")
                        st.divider()
                    st.success(f"**Final Output:** {result.final_output[:500]}")
                    st.metric("Improvement", f"{result.improvement:+.2f} pts")

                elif agent_type == "👥 Crew Agent (Hierarchical)":
                    # Set up crew with default members
                    crew = st.session_state.crew_agent
                    crew.add_member("researcher", "Research specialist", ["research", "search", "find"])
                    crew.add_member("analyst", "Data analyst", ["analyze", "data", "metrics"])
                    crew.add_member("writer", "Content writer", ["write", "document", "report"])
                    result = crew.execute(task=prompt)
                    st.markdown(f"**Manager Notes:** {result.manager_notes}")
                    for t in result.tasks:
                        with st.expander(f"📋 {t.description[:60]}"):
                            st.markdown(t.result[:500] or "No output")
                    st.success(f"**Final Output:** {result.final_output[:500]}")

                elif agent_type == "🔄 Workflow Agent (AutoGen)":
                    wf_pattern = st.session_state.get("wf_pattern", "trio")
                    result = st.session_state.workflow_agent.run(task=prompt, pattern=wf_pattern)
                    for s in result.steps:
                        with st.expander(f"🤖 {s.agent_name.title()}"):
                            st.markdown(s.output[:300])
                    st.success(f"**Final Output:** {result.final_output[:500]}")
                    st.caption(f"Converged: {result.converged} | Tokens: {result.total_tokens}")

                elif agent_type == "Memory Query":
                    result = st.session_state.memory.search(prompt, top_k=5)
                    for i, item in enumerate(result.items):
                        st.markdown(f"{i + 1}. {item.content[:200]}")
                        score_val = result.scores[i] if i < len(result.scores) else None
                        st.caption(f"Score: {score_val:.3f}" if score_val is not None else "Score: N/A")

                elif agent_type == "HITL Approval Workflow":
                    wf = HITLWorkflow()
                    st.session_state.workflow = wf
                    result = wf.run(task=prompt, agent_output=f"Proposed action for: {prompt}", confidence=0.4)
                    st.warning("⚠️ Paused — awaiting human input")
                    st.info("Use the HITL panel on the right to approve or reject.")

                elif agent_type == "Cost-Aware Router":
                    decision = st.session_state.router.route(prompt, agent_type="react", budget=budget)
                    st.json(decision.model_dump())
                    st.session_state.messages.append({"role": "assistant", "content": f"Routed to {decision.model} (${decision.estimated_cost:.5f})"})

                # Record metrics
                elapsed_ms = (_time.monotonic() - start) * 1000
                st.session_state.metrics.record_execution(
                    __import__("src.observability.metrics", fromlist=["AgentMetricsSnapshot"])
                    .AgentMetricsSnapshot(
                        agent_type=agent_type.split(" ")[0].lower(),
                        latency_ms=elapsed_ms,
                        token_count=len(prompt.split()),
                        cost_usd=0.001,
                        iterations=1,
                        success=True,
                    )
                )
                # Evaluate alerts periodically
                if st.session_state.metrics.total_executions % 5 == 0:
                    st.session_state.alerts.evaluate(st.session_state.metrics.summary())

                status.update(label="✅ Complete", state="complete")

    for msg in st.session_state.messages[:-1]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

with col2:
    st.subheader("🛂 HITL Panel")
    if st.session_state.workflow:
        ctx = st.session_state.workflow.get_paused_context()
        if ctx:
            st.warning("⚠️ Workflow Paused")
            st.markdown(f"**Task:** {ctx.task[:200]}")
            st.markdown(f"**Confidence:** {ctx.confidence:.2f}")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Approve", type="primary", use_container_width=True):
                    st.session_state.workflow.provide_human_input(approved=True)
                    st.success("Approved!")
                    st.session_state.workflow = None
                    st.rerun()
            with col_b:
                if st.button("❌ Reject", use_container_width=True):
                    st.session_state.workflow.provide_human_input(approved=False)
                    st.error("Rejected.")
                    st.session_state.workflow = None
                    st.rerun()
        else:
            st.info("No paused workflows.")
    else:
        st.info("Run a HITL workflow from the playground.")

    st.markdown("---")
    st.subheader("🧪 Canary Tests")
    if st.button("▶️ Start Canary Test", use_container_width=True):
        st.session_state.canary.start_canary("model-v2", lambda t: f"[v2: {t[:60]}]", 10)
        st.success("Canary started: model-v2 (10% traffic)")
    if st.session_state.canary.active_canaries:
        for name in st.session_state.canary.active_canaries:
            st.caption(f"🟡 {name} — observing...")

    st.markdown("---")
    st.subheader("🧠 Recent Memory")
    for item in st.session_state.memory.recall_short_term(limit=3):
        with st.container(border=True):
            st.markdown(item.content[:120])
            st.caption(f"Importance: {item.importance:.1f}")
