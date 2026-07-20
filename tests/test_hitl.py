"""
Test cases for Human-in-the-Loop Workflow.

Verify the state machine transitions, pause/resume mechanics,
and full audit trail generation.
"""

import pytest
from src.workflows.hitl_workflow import HITLWorkflow, HITLState


class TestHITLWorkflow:
    """Suite of tests for HITLWorkflow."""

    def setup_method(self) -> None:
        self.wf = HITLWorkflow(confidence_threshold=0.7)

    def test_high_confidence_auto_resolves(self) -> None:
        """If confidence is above threshold, the workflow completes without pause."""
        result = self.wf.run(
            task="Say hello",
            agent_output="Hello!",
            confidence=0.95,
        )
        assert result.success is True
        assert result.final_state == "completed"

    def test_low_confidence_triggers_pause(self) -> None:
        """If confidence is below threshold, the workflow should pause."""
        result = self.wf.run(
            task="Delete all database records",
            agent_output="I can delete all records.",
            confidence=0.3,
            uncertainty_reason="Destructive action with high risk.",
        )
        assert result.final_state == "paused", f"Expected paused, got {result.final_state}"

    def test_human_approval_resumes_workflow(self) -> None:
        """A paused workflow should resume when human approves."""
        self.wf.run(
            task="Deploy to production",
            agent_output="Deploying v2.3.1...",
            confidence=0.5,
            uncertainty_reason="Production deployment requires approval.",
        )
        assert self.wf.current_state == "paused"

        self.wf.provide_human_input(approved=True, input_text="Proceed with deployment.")
        assert self.wf.current_state in ("resume", "completed")

    def test_human_rejection_stops_workflow(self) -> None:
        """A paused workflow should be rejected when human rejects."""
        self.wf.run(
            task="Delete user account",
            agent_output="Deleting account...",
            confidence=0.4,
        )
        self.wf.provide_human_input(approved=False)
        assert self.wf.current_state == "rejected"

    def test_audit_trail_records_all_transitions(self) -> None:
        """The audit trail should contain every state transition."""
        self.wf.run(
            task="Test audit",
            agent_output="Output",
            confidence=0.3,
            human_approved=True,
            human_input="OK",
        )
        trail = self.wf.audit_trail
        assert len(trail) >= 3, f"Expected at least 3 audit entries, got {len(trail)}"

        states = [entry.state for entry in trail]
        assert "input" in states
        assert "analyze" in states
        assert "paused" in states or "completed" in states

    def test_provide_input_without_pause_raises_error(self) -> None:
        """Calling provide_human_input while not paused should raise."""
        self.wf.run(
            task="Simple task",
            agent_output="Simple output",
            confidence=0.95,
        )
        with pytest.raises(RuntimeError, match="Cannot provide input"):
            self.wf.provide_human_input(approved=True)
