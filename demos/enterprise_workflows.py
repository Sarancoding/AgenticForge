#!/usr/bin/env python3
"""
NexusCore Enterprise Workflow Demo — end-to-end demonstration of
real-world business workflows combining multiple agent patterns.

Usage:
    python demos/enterprise_workflows.py
"""

from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.react_agent import ReActAgent
from src.agents.debate_agent import DebateAgent
from src.agents.self_reflective_agent import SelfReflectiveAgent
from src.agents.crew_agent import CrewAgent
from src.agents.workflow_agent import WorkflowAgent
from src.workflows.hitl_workflow import HITLWorkflow
from src.memory.memory_manager import HybridMemory


def demo_customer_support_triage():
    """AI-powered customer support with HITL fallback."""
    print("\n" + "=" * 60)
    print("USE CASE 1: AI-POWERED CUSTOMER SUPPORT TRIAGE")
    print("=" * 60)

    memory = HybridMemory(short_term_capacity=10)
    agent = ReActAgent(max_iterations=5)
    memory.add("Customer: My order #12345 hasn't arrived. It's been 2 weeks.",
               importance=0.9, session_id="support")

    # ReAct handles the triage
    result = agent.run(
        task="The customer's order #12345 is late by 2 weeks. Check the status, "
             "determine the cause, and propose a resolution. If confidence is low, "
             "flag for human review.",
        context=str(memory.recall_long_term("order status", top_k=3)),
    )
    print(f"   Triage result: {'✓' if result.success else '⚠ HITL needed'}")
    print(f"   Iterations: {result.iterations}")
    print(f"   Output: {result.output[:100]}...")
    print("   ✓ Customer support triage complete")


def demo_code_review_pipeline():
    """Multi-agent code review with debate and reflection."""
    print("\n" + "=" * 60)
    print("USE CASE 2: MULTI-AGENT CODE REVIEW PIPELINE")
    print("=" * 60)

    code_snippet = """
def fetch_data(url):
    import requests
    resp = requests.get(url)
    return resp.json()
"""

    # Debate: 3 agents propose improvements
    debate = DebateAgent(num_proposers=3)
    debate_result = debate.debate(
        f"Review this Python code and suggest improvements:\n{code_snippet}"
    )
    print(f"   Debate: {len(debate_result.proposals)} proposals generated")
    print(f"   Winner: Debater #{debate_result.winner.agent_id} (score: {debate_result.winner.critic_score:.1f})")

    # Self-reflection on the review quality
    reflective = SelfReflectiveAgent(max_reflections=2)
    reflect_result = reflective.reflect(
        f"Evaluate the quality of this code review: {debate_result.consensus_output[:200]}"
    )
    print(f"   Self-reflection: improvement of {reflect_result.improvement:+.2f} pts")
    print("   ✓ Code review pipeline complete")


def demo_crew_research_report():
    """Crew of specialists researching and writing a report."""
    print("\n" + "=" * 60)
    print("USE CASE 3: CREW RESEARCH REPORT GENERATION")
    print("=" * 60)

    crew = CrewAgent()
    crew.add_member("researcher", "Research specialist", ["research", "search", "find"])
    crew.add_member("analyst", "Data analyst", ["analyze", "data", "metrics"])
    crew.add_member("writer", "Content writer", ["write", "document", "report"])

    result = crew.execute(
        "Research and write a brief report on the impact of generative AI "
        "on the software development industry in 2026."
    )
    print(f"   Crew members: {crew.member_count}")
    print(f"   Subtasks: {len(result.tasks)}")
    print(f"   Final output ({len(result.final_output)} chars)")
    print(f"   Manager notes: {result.manager_notes[:100]}...")
    print("   ✓ Crew research report complete")


def demo_hitl_approval_workflow():
    """Human-in-the-loop approval for sensitive operations."""
    print("\n" + "=" * 60)
    print("USE CASE 4: HITL APPROVAL FOR SENSITIVE OPERATIONS")
    print("=" * 60)

    wf = HITLWorkflow(confidence_threshold=0.7)
    result = wf.run(
        task="Delete production database 'users' table",
        agent_output="DROP TABLE users;",
        confidence=0.3,
        uncertainty_reason="Destructive operation with no rollback",
    )
    print(f"   Initial state: {result.final_state} (paused for approval)")

    # Human approves
    wf.provide_human_input(approved=True, input_text="Add WHERE clause first, then proceed")
    print(f"   After approval: {wf.current_state}")
    print(f"   Audit entries: {len(wf.audit_trail)}")
    print("   ✓ HITL approval workflow complete")


def demo_workflow_agent():
    """AutoGen-style workflow agent for multi-step tasks."""
    print("\n" + "=" * 60)
    print("USE CASE 5: WORKFLOW AGENT (AUTOGEN-STYLE)")
    print("=" * 60)

    workflow = WorkflowAgent()

    for pattern in ["trio", "reflect"]:
        result = workflow.run(
            "Design a simple REST API for a todo application with CRUD operations.",
            pattern=pattern,
        )
        print(f"   Pattern '{pattern}': {len(result.steps)} steps, "
              f"{result.total_tokens} tokens, converged={result.converged}")

    print("   ✓ Workflow agent demo complete")


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║    NexusCore Enterprise Workflow Demo Suite     ║")
    print("╚══════════════════════════════════════════════════╝")

    demo_customer_support_triage()
    demo_code_review_pipeline()
    demo_crew_research_report()
    demo_hitl_approval_workflow()
    demo_workflow_agent()

    print("\n" + "=" * 60)
    print("✅ All enterprise workflow demos completed!")
    print("=" * 60)
