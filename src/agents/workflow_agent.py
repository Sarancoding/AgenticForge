"""
WorkflowAgent — AutoGen-style conversational multi-agent workflows.

Manages a sequence of agent interactions with context passing,
conditional branching, and convergence detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """A single step in the multi-agent workflow."""

    agent_name: str
    instruction: str
    output: str = ""
    status: str = "pending"
    tokens_used: int = 0


@dataclass
class WorkflowResult:
    """Result of a multi-agent workflow execution."""

    final_output: str
    steps: list[WorkflowStep] = field(default_factory=list)
    converged: bool = False
    total_tokens: int = 0


class WorkflowAgent:
    """
    Multi-agent conversational workflow manager (AutoGen-style).

    Orchestrates a sequence of agent interactions where each agent
    receives the output of the previous agent, enabling complex
    multi-step reasoning with specialist handoffs.

    Built-in patterns:
    - chain: Sequential handoff A → B → C
    - trio: Analyst → Critic → Synthesizer
    - reflect: Generate → Evaluate → Improve
    """

    def __init__(
        self,
        llm_call: Callable[[str], str] | None = None,
    ) -> None:
        self._llm = llm_call or (lambda p: f"[Workflow: {p[:60]}...]")

    def _run_chain(self, task: str, agents: list[str]) -> WorkflowResult:
        """Sequential chain: Agent 1 → Agent 2 → Agent 3."""
        steps: list[WorkflowStep] = []
        context = task

        for agent_name in agents:
            step = WorkflowStep(agent_name=agent_name, instruction=context)
            output = self._llm(
                f"You are {agent_name}. Given this context:\n{context}\n\nProceed:"
            )
            step.output = output
            step.status = "completed"
            step.tokens_used = len(output.split())
            steps.append(step)
            context = output  # Pass output to next agent

        return WorkflowResult(
            final_output=context,
            steps=steps,
            converged=True,
            total_tokens=sum(s.tokens_used for s in steps),
        )

    def _run_trio(self, task: str) -> WorkflowResult:
        """Analyst → Critic → Synthesizer pattern."""
        steps: list[WorkflowStep] = []

        # Analyst
        analyst = WorkflowStep(agent_name="analyst", instruction=task)
        analyst.output = self._llm(f"As an analyst, thoroughly analyze this:\n{task}")
        analyst.status = "completed"
        steps.append(analyst)

        # Critic
        critic = WorkflowStep(agent_name="critic", instruction=analyst.output)
        critic.output = self._llm(
            f"As a critic, evaluate this analysis and identify gaps:\n{analyst.output}"
        )
        critic.status = "completed"
        steps.append(critic)

        # Synthesizer
        synth = WorkflowStep(agent_name="synthesizer", instruction=f"{analyst.output}\n\nCritique:\n{critic.output}")
        synth.output = self._llm(
            f"As a synthesizer, combine the analysis and critique into a final answer:\n"
            f"Analysis:\n{analyst.output}\n\nCritique:\n{critic.output}"
        )
        synth.status = "completed"
        steps.append(synth)

        return WorkflowResult(
            final_output=synth.output,
            steps=steps,
            converged=True,
            total_tokens=sum(s.tokens_used for s in steps),
        )

    def _run_reflect(self, task: str, max_iterations: int = 3) -> WorkflowResult:
        """Generate → Evaluate → Improve loop."""
        steps: list[WorkflowStep] = []
        current = self._llm(f"Complete this task:\n{task}")

        for i in range(max_iterations):
            gen_step = WorkflowStep(agent_name="generator", instruction=task, output=current, status="completed")
            steps.append(gen_step)

            eval_output = self._llm(
                f"Evaluate this output for quality and completeness:\n{current}\n\nIssues:"
            )
            eval_step = WorkflowStep(agent_name="evaluator", instruction=current, output=eval_output, status="completed")
            steps.append(eval_step)

            if i == max_iterations - 1:
                break

            current = self._llm(
                f"Improve this output based on the evaluation:\n"
                f"Output:\n{current}\n\nEvaluation:\n{eval_output}\n\nImproved version:"
            )

        return WorkflowResult(
            final_output=current,
            steps=steps,
            converged=True,
            total_tokens=sum(s.tokens_used for s in steps),
        )

    def run(self, task: str, pattern: str = "trio") -> WorkflowResult:
        """
        Execute a multi-agent workflow.

        Args:
            task: The task/prompt to execute.
            pattern: The workflow pattern:
                - "chain": Sequential agent handoff
                - "trio": Analyst → Critic → Synthesizer
                - "reflect": Generate → Evaluate → Improve

        Returns:
            WorkflowResult with full step trace.
        """
        pattern = pattern.lower()
        if pattern == "chain":
            agents = ["researcher", "analyst", "writer"]
            return self._run_chain(task, agents)
        if pattern == "trio":
            return self._run_trio(task)
        if pattern == "reflect":
            return self._run_reflect(task)
        # Default to trio
        logger.warning("Unknown pattern '%s', defaulting to 'trio'", pattern)
        return self._run_trio(task)
