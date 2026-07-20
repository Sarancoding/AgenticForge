"""
Test cases for the Cost-Aware Router.

Verify that the router selects cheaper models for simple tasks
and respects per-task budgets.
"""

from src.agents.router import CostAwareRouter, ComplexityTier


class TestCostAwareRouter:
    """Suite of tests for CostAwareRouter."""

    def setup_method(self) -> None:
        self.router = CostAwareRouter(default_budget=0.10)

    def test_simple_task_gets_low_tier(self) -> None:
        """A very simple query should be classified as LOW complexity."""
        tier = self.router.estimate_complexity("What is the weather today?")
        assert tier == ComplexityTier.LOW, f"Expected LOW, got {tier}"

    def test_technical_task_gets_high_tier(self) -> None:
        """A task with technical keywords should be at least MEDIUM."""
        tier = self.router.estimate_complexity(
            "Implement a microservices architecture with Kubernetes and Docker."
        )
        assert tier.value >= ComplexityTier.MEDIUM.value, f"Expected >= MEDIUM, got {tier}"

    def test_long_multistep_task_gets_high_tier(self) -> None:
        """A long, multi-sentence task should be classified as HIGH."""
        task = (
            "Analyze the following codebase and identify performance bottlenecks. "
            "Then propose optimizations for the database queries, API response times, "
            "and frontend rendering. Finally, generate a detailed report."
        )
        tier = self.router.estimate_complexity(task)
        assert tier == ComplexityTier.HIGH, f"Expected HIGH, got {tier}"

    def test_cheap_model_for_simple_task(self) -> None:
        """The router should select gpt-4o-mini for a low-complexity task."""
        decision = self.router.route("What is 2+2?", agent_type="react")
        assert decision.model == "gpt-4o-mini", f"Expected gpt-4o-mini, got {decision.model}"

    def test_budget_respected(self) -> None:
        """When budget is very tight, the router should degrade to a cheaper model."""
        decision = self.router.route(
            "Implement a complete distributed caching system",
            agent_type="react",
            budget=0.001,  # $0.001 — extremely tight
        )
        # Should have degraded to the cheapest model
        assert decision.estimated_cost <= 0.001, f"Cost {decision.estimated_cost} exceeds budget"

    def test_routing_decision_has_all_fields(self) -> None:
        """A RoutingDecision should contain all expected metadata."""
        decision = self.router.route("Hello world", agent_type="react")
        assert decision.agent_type == "react"
        assert decision.model
        assert decision.estimated_input_tokens > 0
        assert decision.estimated_cost >= 0.0
        assert decision.budget_remaining >= 0.0

    def test_estimate_tokens_positive(self) -> None:
        """Token estimate should always be positive."""
        tokens = self.router._estimate_tokens("Hi")  # noqa: SLF001
        assert tokens > 0
