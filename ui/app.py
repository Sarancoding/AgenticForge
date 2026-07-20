"""
NexusCore — Streamlit Testing Dashboard

Interactive web UI to select agent archetypes, input tasks,
view real-time ReAct logs, approve/reject HITL steps,
and explore cost analytics.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import streamlit as st

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.router import CostAwareRouter  # noqa: E402
from src.agents.react_agent import ReActAgent  # noqa: E402
from src.agents.debate_agent import DebateAgent  # noqa: E402
from src.agents.self_reflective_agent import SelfReflectiveAgent  # noqa: E402
from src.memory.memory_manager import HybridMemory  # noqa: E402
from src.workflows.hitl_workflow import HITLWorkflow  # noqa: E402

# ─── Page Config ───────────────────────────────────────────────────

st.set_page_config(
    page_title="NexusCore Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚡ NexusCore Agentic Platform")
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
if "memory" not in st.session_state:
    st.session_state.memory = HybridMemory()
if "workflow" not in st.session_state:
    st.session_state.workflow = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ─── Sidebar ───────────────────────────────────────────────────────

with st.sidebar:
    st.header("🧭 Agent Controls")

    agent_type = st.selectbox(
        "Select Agent Archetype",
        options=[
            "ReAct Planning Agent",
            "Multi-Agent Debate",
            "Self-Reflective Agent",
            "Memory Query",
            "HITL Approval Workflow",
            "Cost-Aware Router",
        ],
        index=0,
    )

    st.markdown("---")
    st.subheader("⚙️ Configuration")

    max_iterations = st.slider("Max Iterations", 1, 20, 5, help="Hard stop for ReAct loops")
    st.session_state.react_agent.max_iterations = max_iterations

    budget = st.number_input(
        "Token Budget ($)",
        min_value=0.001,
        max_value=1.0,
        value=0.10,
        step=0.01,
        format="%.3f",
        help="Maximum USD cost per task",
    )

    st.markdown("---")
    st.subheader("📊 Cost Analytics")

    if st.button("🔄 Estimate Cost for Task"):
        if task_input := st.session_state.get("task_input", ""):
            decision = st.session_state.router.route(task_input, agent_type="react", budget=budget)
            st.metric("Estimated Cost", f"${decision.estimated_cost:.5f}")
            st.metric("Model", decision.model)
            st.metric("Budget Remaining", f"${decision.budget_remaining:.5f}")
            st.caption(f"Tier: {decision.tier.name} | Tokens: ~{decision.estimated_input_tokens}")
        else:
            st.warning("Enter a task first.")

    st.markdown("---")
    st.caption("NexusCore v0.1.0")

# ─── Main Content ──────────────────────────────────────────────────

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("💬 Agent Playground")

    # Chat input
    prompt = st.chat_input("Enter your task for the agent...")
    if prompt:
        st.session_state.task_input = prompt
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="⚡"):
            with st.status("Thinking...", expanded=True) as status:
                if agent_type == "ReAct Planning Agent":
                    result = st.session_state.react_agent.run(task=prompt)

                    # Log each step
                    for i, step in enumerate(result.steps):
                        st.markdown(f"**Step {i + 1} — {step.phase.value.upper()}**")
                        if step.thought:
                            st.info(f"💭 {step.thought[:300]}")
                        if step.action:
                            st.text(f"⚡ Action: {step.action[:300]}")
                        if step.reflection:
                            st.text(f"🪞 Reflection: {step.reflection[:300]}")
                        st.caption(f"Confidence: {step.confidence:.2f}")
                        st.divider()

                    status.update(label="✅ Complete!", state="complete")
                    final = result.output
                    st.session_state.messages.append({"role": "assistant", "content": final})
                    st.markdown(final)

                elif agent_type == "Multi-Agent Debate":
                    debate_agent = st.session_state.debate_agent
                    debate_agent.num_proposers = 3
                    result = debate_agent.debate(task=prompt)

                    for p in result.proposals:
                        with st.expander(f"🤖 Debater #{p.agent_id} — Score: {p.critic_score:.1f}"):
                            st.markdown(p.content[:500])

                    st.success(f"**Consensus:** {result.consensus_output[:500]}")
                    if result.winner:
                        st.metric("Winner", f"Debater #{result.winner.agent_id}", f"Score: {result.winner.critic_score:.1f}")

                    status.update(label="✅ Debate complete!", state="complete")

                elif agent_type == "Self-Reflective Agent":
                    result = st.session_state.reflective_agent.reflect(task=prompt)

                    st.subheader("📈 Reflection Metrics")
                    for m in result.metrics:
                        st.markdown(f"**Iteration {m.iteration}** — Score: {m.score:.1f}/10")
                        st.text(f"Critique: {m.critique[:200]}")
                        st.divider()

                    st.success(f"**Final Output:** {result.final_output[:500]}")
                    st.metric("Improvement", f"{result.improvement:+.2f} pts")
                    status.update(label="✅ Reflection complete!", state="complete")

                elif agent_type == "Memory Query":
                    result = st.session_state.memory.search(prompt, top_k=5)
                    st.session_state.messages.append({"role": "assistant", "content": f"Memory results: {len(result.items)} items"})
                    for i, item in enumerate(result.items):
                        st.markdown(f"{i + 1}. {item.content[:200]}")
                        score_val = result.scores[i] if i < len(result.scores) else None
                        st.caption(f"Score: {score_val:.3f}" if score_val is not None else "Score: N/A")
                    status.update(label="✅ Query complete!", state="complete")

                elif agent_type == "HITL Approval Workflow":
                    wf = HITLWorkflow()
                    st.session_state.workflow = wf
                    result = wf.run(task=prompt, agent_output=f"Proposed action for: {prompt}", confidence=0.4)
                    st.warning(f"⚠️ Paused — confidence {0.4:.2f} below threshold")
                    st.info("Use the HITL panel on the right to approve or reject.")
                    status.update(label="⏸️ Awaiting human input", state="error")

                elif agent_type == "Cost-Aware Router":
                    decision = st.session_state.router.route(prompt, agent_type="react", budget=budget)
                    st.json(decision.model_dump())
                    st.session_state.messages.append({"role": "assistant", "content": f"Routed to {decision.model} (${decision.estimated_cost:.5f})"})
                    status.update(label="✅ Route calculated!", state="complete")

                # Store in memory
                st.session_state.memory.add(
                    content=f"User: {prompt}\nAssistant: {st.session_state.messages[-1]['content'][:200]}",
                    importance=0.7,
                    session_id="dashboard",
                )

    # Display message history
    for msg in st.session_state.messages[:-1]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

with col2:
    st.subheader("🛂 HITL Panel")

    if st.session_state.workflow:
        wf = st.session_state.workflow
        ctx = wf.get_paused_context()
        if ctx:
            st.warning("Workflow is paused")
            st.markdown(f"**Task:** {ctx.task[:200]}")
            st.markdown(f"**Proposed:** {ctx.agent_output[:200]}")
            st.markdown(f"**Confidence:** {ctx.confidence:.2f}")
            st.markdown(f"**Reason:** {ctx.uncertainty_reason or 'N/A'}")

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Approve", type="primary", use_container_width=True):
                    wf.provide_human_input(approved=True, input_text="Approved via dashboard.")
                    st.success("✅ Approved! Workflow resuming.")
                    st.session_state.workflow = None
                    st.rerun()
            with col_b:
                if st.button("❌ Reject", type="secondary", use_container_width=True):
                    wf.provide_human_input(approved=False)
                    st.error("❌ Rejected. Workflow stopped.")
                    st.session_state.workflow = None
                    st.rerun()
        else:
            st.info("No paused workflows.")
    else:
        st.info("No paused workflows. Run a HITL workflow from the playground.")

    st.markdown("---")
    st.subheader("🧠 Recent Memory")
    recent = st.session_state.memory.recall_short_term(limit=5)
    for item in recent:
        with st.container(border=True):
            st.markdown(item.content[:150])
            st.caption(f"Importance: {item.importance:.1f}")
