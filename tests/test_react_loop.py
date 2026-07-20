"""
Test cases for the ReAct planning agent.

Verify that the agent stops after max iterations, handles tool failures
gracefully, and triggers HITL when confidence is low.
"""

from src.agents.react_agent import ReActAgent, LoopPhase


class TestReActLoop:
    """Suite of tests for ReActAgent."""

    def setup_method(self) -> None:
        self.agent = ReActAgent(max_iterations=3, confidence_threshold=0.0)

    def test_max_iterations_hard_stop(self) -> None:
        """The agent should stop after max_iterations, not loop forever."""
        self.agent.max_iterations = 2
        result = self.agent.run("Count from 1 to 100")
        assert result.iterations == 2, f"Expected 2 iterations, got {result.iterations}"

    def test_hitl_triggered_on_low_confidence(self) -> None:
        """When confidence is below threshold, the agent should stop and flag HITL."""
        self.agent.confidence_threshold = 0.9  # Impossible to reach with stub LLM
        result = self.agent.run("Explain quantum computing")
        assert result.success is False, "Expected failure (HITL trigger)"
        assert result.error is not None and "HITL" in result.error, "Expected HITL error message"

    def test_early_exit_on_high_confidence(self) -> None:
        """If confidence is high enough, the agent should exit early."""
        self.agent.early_exit_confidence = 0.0  # Always exit immediately
        result = self.agent.run("Say hello")
        assert result.success is True
        assert result.iterations == 1, f"Expected 1 iteration (early exit), got {result.iterations}"

    def test_steps_are_recorded(self) -> None:
        """Each iteration should produce a ReActStep with all phases."""
        self.agent.max_iterations = 1
        result = self.agent.run("Test step recording")
        assert len(result.steps) == 1
        step = result.steps[0]
        assert step.observation
        assert step.thought
        assert step.action

    def test_tool_failure_graceful_degradation(self) -> None:
        """A failing tool should not crash the agent — it should degrade gracefully."""
        def failing_tool() -> str:
            raise RuntimeError("Tool crashed!")

        result = self.agent.run(
            "Use the broken tool",
            tools={"broken": failing_tool},
        )
        # Should still complete without exception
        assert result.output
