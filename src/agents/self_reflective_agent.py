"""
Self-reflective agent with auto-evaluation — execute, LLM-as-judge evaluation,
critique reasoning, constrained regeneration, and improvement metric logging.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class EvalMetric:
    """Metrics from a single evaluation cycle."""

    iteration: int
    score: float
    critique: str
    output: str


@dataclass
class ReflectiveResult:
    """Result of a self-reflective agent run."""

    final_output: str
    metrics: list[EvalMetric] = field(default_factory=list)
    improvement: float = 0.0


class SelfReflectiveAgent:
    """
    Self-reflective agent that evaluates its own output and iteratively improves it.

    Flow:
    1. Execute: Generate initial output.
    2. Evaluate: LLM-as-judge scores the output (1-10) with critique.
    3. Critique Reasoning: Analyze critique to identify specific weaknesses.
    4. Regenerate: Produce improved output with critique as constraints.
    5. Repeat until score threshold met or max iterations reached.
    6. Log improvement metrics.
    """

    def __init__(
        self,
        max_reflections: int = 3,
        score_threshold: float = 8.0,
        llm_call: Callable[[str], str] | None = None,
    ) -> None:
        """
        Args:
            max_reflections: Maximum number of reflect-improve cycles.
            score_threshold: Exit when the evaluation score reaches this.
            llm_call: Function to call the LLM.
        """
        self.max_reflections = max_reflections
        self.score_threshold = score_threshold
        self._llm = llm_call or (lambda p: f"[Eval for: {p[:60]}...]")

    def execute(self, task: str) -> str:
        """Generate an initial output for the task."""
        return self._llm(f"Complete this task:\n{task}")

    def evaluate(self, task: str, output: str) -> tuple[float, str]:
        """
        LLM-as-judge: score the output (1-10) and provide critique.
        Returns (score, critique).
        """
        result = self._llm(
            f"Task: {task}\n\nOutput: {output}\n\n"
            f"Score this output from 1 to 10 on quality, correctness, and completeness.\n"
            f"Then provide a brief critique.\n\nScore:"
        )
        lines = result.strip().split("\n")
        try:
            score = float(lines[0].strip())
        except (ValueError, TypeError):
            score = 5.0
        critique = "\n".join(lines[1:]).strip() or "No detailed critique."
        return min(max(score, 1.0), 10.0), critique

    def regenerate(self, task: str, previous_output: str, critique: str) -> str:
        """Generate an improved output using the critique as a constraint."""
        return self._llm(
            f"Task: {task}\n\nPrevious Output:\n{previous_output}\n\n"
            f"Critique of previous output:\n{critique}\n\n"
            f"Generate an improved version that addresses the critique above."
        )

    def reflect(self, task: str) -> ReflectiveResult:
        """
        Run the self-reflective improvement loop.

        Args:
            task: The task to execute and iteratively improve.

        Returns:
            ReflectiveResult with the best output and improvement metrics.
        """
        metrics: list[EvalMetric] = []
        current_output = self.execute(task)
        best_score = 0.0
        best_output = current_output

        for iteration in range(1, self.max_reflections + 1):
            score, critique = self.evaluate(task, current_output)
            metrics.append(EvalMetric(iteration=iteration, score=score, critique=critique, output=current_output))

            if score > best_score:
                best_score = score
                best_output = current_output

            logger.info("Reflection %d: score=%.1f/10", iteration, score)

            if score >= self.score_threshold:
                logger.info("Score threshold (%.1f) met at iteration %d.", self.score_threshold, iteration)
                break

            current_output = self.regenerate(task, current_output, critique)

        improvement = (metrics[-1].score - metrics[0].score) if len(metrics) > 1 else 0.0
        return ReflectiveResult(final_output=best_output, metrics=metrics, improvement=round(improvement, 2))
