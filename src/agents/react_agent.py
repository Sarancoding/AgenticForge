"""
ReAct planning agent — Observe → Think → Act → Reflect loop
with self-critique, max iteration limits, and graceful degradation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class LoopPhase(Enum):
    OBSERVE = "observe"
    THINK = "think"
    ACT = "act"
    REFLECT = "reflect"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ReActStep:
    """A single step in the ReAct loop."""

    phase: LoopPhase
    observation: str = ""
    thought: str = ""
    action: str = ""
    reflection: str = ""
    confidence: float = 0.0


@dataclass
class ReActResult:
    """The final result of a ReAct agent run."""

    success: bool
    output: str
    steps: list[ReActStep] = field(default_factory=list)
    iterations: int = 0
    error: str | None = None


class ReActAgent:
    """
    ReAct planning agent implementing the Observe → Think → Act → Reflect loop.

    Features:
    - Configurable max iterations with hard stop
    - Self-critique after each action
    - Graceful degradation on tool failure
    - Confidence-based early exit
    - HITL trigger when confidence is low
    """

    def __init__(
        self,
        max_iterations: int = 15,
        confidence_threshold: float = 0.3,
        early_exit_confidence: float = 0.9,
        llm_call: Callable[[str], str] | None = None,
    ) -> None:
        """
        Args:
            max_iterations: Hard limit on think-act cycles.
            confidence_threshold: If confidence drops below this, trigger HITL.
            early_exit_confidence: If confidence reaches this, exit early.
            llm_call: Function to call the LLM. Defaults to a stub.
        """
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.early_exit_confidence = early_exit_confidence
        self._llm = llm_call or self._default_llm

    @staticmethod
    def _default_llm(prompt: str) -> str:
        """Stub LLM call — replace with actual model invocation."""
        return f"[Simulated response to: {prompt[:80]}...]"

    def observe(self, task: str, context: str = "") -> str:
        """Parse the input and gather context."""
        return f"Task: {task}\nContext: {context or 'No prior context.'}"

    def think(self, observation: str) -> tuple[str, float]:
        """
        Generate a reasoning step and confidence score.
        Returns (thought, confidence).
        """
        thought = self._llm(f"Given this observation: {observation}\nWhat should I do next?")
        confidence_raw = self._llm(
            f"Rate your confidence in this plan on a scale of 0.0 to 1.0: {thought}\nConfidence:"
        )
        try:
            confidence = float(confidence_raw.strip())
        except (ValueError, TypeError):
            confidence = 0.5
        return thought, min(max(confidence, 0.0), 1.0)

    def act(self, thought: str, tools: dict[str, Callable] | None = None) -> str:
        """Execute a tool or produce a direct response."""
        if tools:
            for name, tool_fn in tools.items():
                if name.lower() in thought.lower():
                    try:
                        return tool_fn()
                    except Exception as exc:
                        logger.warning("Tool %s failed: %s", name, exc)
                        return f"[Tool {name} failed: {exc}]"
        return self._llm(f"Execute this plan and produce output:\n{thought}")

    def reflect(self, action_result: str) -> tuple[str, float]:
        """
        Self-critique the action result.
        Returns (reflection, improved confidence).
        """
        reflection = self._llm(
            f"Critique this output and suggest improvements:\n{action_result}\nCritique:"
        )
        improved_confidence_raw = self._llm(
            f"After critique, rate your confidence (0.0 to 1.0):\n{reflection}\nConfidence:"
        )
        try:
            confidence = float(improved_confidence_raw.strip())
        except (ValueError, TypeError):
            confidence = 0.5
        return reflection, min(max(confidence, 0.0), 1.0)

    def run(
        self,
        task: str,
        tools: dict[str, Callable] | None = None,
        context: str = "",
    ) -> ReActResult:
        """
        Execute the full ReAct loop.

        Args:
            task: The user's task/prompt.
            tools: Optional dict of tool name → callable.
            context: Optional prior context string.

        Returns:
            ReActResult with the final output and full step trace.
        """
        steps: list[ReActStep] = []
        current_context = context
        output = ""

        for iteration in range(self.max_iterations):
            # Observe
            observation = self.observe(task, current_context)
            step = ReActStep(phase=LoopPhase.OBSERVE, observation=observation)

            # Think
            thought, confidence = self.think(observation)
            step.thought = thought
            step.confidence = confidence

            # Early exit check
            if confidence >= self.early_exit_confidence:
                step.phase = LoopPhase.DONE
                step.action = "Early exit — high confidence achieved."
                output = thought
                steps.append(step)
                logger.info("Early exit at iteration %d (confidence=%.2f)", iteration, confidence)
                return ReActResult(success=True, output=output, steps=steps, iterations=iteration + 1)

            # HITL trigger
            if confidence < self.confidence_threshold:
                step.phase = LoopPhase.FAILED
                step.reflection = f"Confidence {confidence:.2f} below threshold {self.confidence_threshold}. Triggering HITL."
                steps.append(step)
                logger.warning("HITL triggered at iteration %d (confidence=%.2f)", iteration, confidence)
                return ReActResult(
                    success=False,
                    output="HITL pause requested — confidence too low.",
                    steps=steps,
                    iterations=iteration + 1,
                    error=step.reflection,
                )

            # Act
            action_result = self.act(thought, tools)
            step.action = action_result

            # Reflect
            reflection, improved_confidence = self.reflect(action_result)
            step.reflection = reflection
            step.confidence = improved_confidence

            steps.append(step)
            current_context = f"{current_context}\nThought: {thought}\nAction: {action_result}\nReflection: {reflection}"
            output = action_result

            if improved_confidence >= self.early_exit_confidence:
                step.phase = LoopPhase.DONE
                logger.info("Post-reflection early exit at iteration %d (confidence=%.2f)", iteration, improved_confidence)
                return ReActResult(success=True, output=output, steps=steps, iterations=iteration + 1)

            step.phase = LoopPhase.REFLECT

        # Max iterations reached
        logger.info("Max iterations (%d) reached.", self.max_iterations)
        return ReActResult(
            success=True,
            output=output or "Max iterations reached with partial result.",
            steps=steps,
            iterations=self.max_iterations,
        )
