"""
Human-in-the-Loop (HITL) workflow — state graph definition for
pausing execution, waiting for human approval, and resuming
with validated context and full audit trails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HITLState(Enum):
    INPUT = "input"
    ANALYZE = "analyze"
    PAUSED = "paused"
    VALIDATE = "validate"
    RESUME = "resume"
    COMPLETED = "completed"
    REJECTED = "rejected"


@dataclass
class AuditEntry:
    """A single audit trail entry."""

    timestamp: str
    state: str
    action: str
    details: str = ""


@dataclass
class HITLContext:
    """
    The full context snapshot captured when a workflow pauses.

    This ensures that when the workflow resumes, it has the exact
    context it had when it paused.
    """

    task: str
    agent_output: str | None = None
    confidence: float = 0.0
    uncertainty_reason: str = ""
    human_input: str | None = None
    approved: bool | None = None


@dataclass
class HITLResult:
    """Result of a HITL workflow execution."""

    success: bool
    output: str | None = None
    audit_trail: list[AuditEntry] = field(default_factory=list)
    final_state: str = ""


class HITLWorkflow:
    """
    Human-in-the-Loop workflow manager.

    State machine:
    INPUT → ANALYZE → [Confidence > Threshold?]
        ├── Yes → COMPLETED
        └── No  → PAUSED → VALIDATE → [Approved?]
                ├── Yes → RESUME → COMPLETED
                └── No  → REJECTED

    Features:
    - Uncertainty detection pauses the workflow
    - Full context snapshot captured at pause time
    - Human input validated before resumption
    - Complete audit trail of every state transition
    """

    def __init__(self, confidence_threshold: float = 0.7) -> None:
        """
        Args:
            confidence_threshold: Minimum confidence to auto-proceed (0.0 to 1.0).
        """
        self._threshold = confidence_threshold
        self._current_state: HITLState = HITLState.INPUT
        self._audit_trail: list[AuditEntry] = []
        self._context: HITLContext | None = None

    def _log(self, state: str, action: str, details: str = "") -> None:
        """Add an entry to the audit trail."""
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            state=state,
            action=action,
            details=details,
        )
        self._audit_trail.append(entry)
        logger.info("[HITL] %s → %s: %s", state, action, details)

    def _transition_to(self, new_state: HITLState, reason: str = "") -> None:
        """Transition to a new state and log it."""
        old_state = self._current_state.value
        self._current_state = new_state
        self._log(old_state, new_state.value, reason)

    def analyze(self, task: str, agent_output: str, confidence: float, reason: str = "") -> HITLState:
        """
        Analyze whether the workflow should pause for human input.

        Args:
            task: The original task.
            agent_output: The agent's proposed output/action.
            confidence: The agent's confidence score (0.0 to 1.0).
            reason: Optional reason for low confidence.

        Returns:
            The next HITLState (PAUSED or COMPLETED).
        """
        self._context = HITLContext(
            task=task,
            agent_output=agent_output,
            confidence=confidence,
            uncertainty_reason=reason,
        )

        self._transition_to(HITLState.ANALYZE, f"Confidence={confidence:.2f}, threshold={self._threshold:.2f}")

        if confidence >= self._threshold:
            self._transition_to(HITLState.COMPLETED, "Sufficient confidence — auto-resolving.")
            return HITLState.COMPLETED

        self._transition_to(HITLState.PAUSED, reason or f"Confidence {confidence:.2f} below threshold.")
        return HITLState.PAUSED

    def provide_human_input(self, approved: bool, input_text: str | None = None) -> HITLState:
        """
        Provide human input for a paused workflow.

        Args:
            approved: Whether the human approves the agent's proposed action.
            input_text: Optional human-provided correction or instruction.

        Returns:
            The next HITLState (RESUME or REJECTED).
        """
        if self._current_state != HITLState.PAUSED:
            raise RuntimeError(f"Cannot provide input in state '{self._current_state.value}'. Must be 'paused'.")

        if self._context is None:
            raise RuntimeError("No context snapshot found. Cannot resume.")

        self._context.human_input = input_text
        self._context.approved = approved

        self._transition_to(HITLState.VALIDATE, f"Approved={approved}, input={input_text or 'none'}")

        if approved:
            self._transition_to(HITLState.RESUME, "Human approved — resuming workflow.")
            self._transition_to(HITLState.COMPLETED, "Workflow completed after human approval.")
            return HITLState.RESUME

        self._transition_to(HITLState.REJECTED, "Human rejected the proposed action.")
        return HITLState.REJECTED

    def get_paused_context(self) -> HITLContext | None:
        """Get the context snapshot for a paused workflow (for UI rendering)."""
        if self._current_state == HITLState.PAUSED:
            return self._context
        return None

    def run(
        self,
        task: str,
        agent_output: str,
        confidence: float,
        uncertainty_reason: str = "",
        human_approved: bool | None = None,
        human_input: str | None = None,
    ) -> HITLResult:
        """
        Run the HITL workflow end-to-end.

        Args:
            task: The original task description.
            agent_output: The agent's proposed output.
            confidence: Confidence score (0.0 to 1.0).
            uncertainty_reason: Explanation of low confidence.
            human_approved: If provided, simulates human input immediately.
            human_input: Optional human instruction.

        Returns:
            HITLResult with the final output and full audit trail.
        """
        # 1. Analyze
        state = self.analyze(task, agent_output, confidence, uncertainty_reason)

        # 2. If paused and human input is provided immediately, use it
        if state == HITLState.PAUSED and human_approved is not None:
            state = self.provide_human_input(human_approved, human_input)

        # 3. Build result
        output = agent_output
        if self._context and self._context.approved and self._context.human_input:
            output = f"{agent_output}\n\n[Human revised: {self._context.human_input}]"

        return HITLResult(
            success=state in (HITLState.COMPLETED, HITLState.RESUME),
            output=output,
            audit_trail=self._audit_trail,
            final_state=self._current_state.value,
        )

    @property
    def current_state(self) -> str:
        return self._current_state.value

    @property
    def audit_trail(self) -> list[AuditEntry]:
        return self._audit_trail.copy()
