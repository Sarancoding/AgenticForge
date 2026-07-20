"""
Cost-aware agent router — selects the optimal agent and model
based on task complexity, token budget, and cost constraints.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ComplexityTier(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


# Model → cost-per-1K-tokens mapping (USD, approximate)
MODEL_COST_MAP: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.000_15, "output": 0.000_60},
    "gpt-4o": {"input": 0.002_50, "output": 0.010_00},
    "o1-mini": {"input": 0.003_00, "output": 0.012_00},
    "o1-preview": {"input": 0.015_00, "output": 0.060_00},
}

TIER_MODEL_MAP: dict[ComplexityTier, str] = {
    ComplexityTier.LOW: "gpt-4o-mini",
    ComplexityTier.MEDIUM: "gpt-4o",
    ComplexityTier.HIGH: "o1-mini",
    ComplexityTier.VERY_HIGH: "o1-preview",
}

TIER_TOKEN_CEILING: dict[ComplexityTier, int] = {
    ComplexityTier.LOW: 500,
    ComplexityTier.MEDIUM: 2_000,
    ComplexityTier.HIGH: 8_000,
    ComplexityTier.VERY_HIGH: 16_000,
}


class RoutingDecision(BaseModel):
    """The result of a routing decision."""

    agent_type: str = Field(description="The selected agent archetype")
    model: str = Field(description="The selected LLM model name")
    tier: ComplexityTier = Field(description="Estimated complexity tier")
    estimated_input_tokens: int = Field(ge=0, description="Estimated token count")
    estimated_cost: float = Field(ge=0.0, description="Estimated cost in USD")
    budget_remaining: float = Field(ge=0.0, description="Remaining budget after this call")


class CostAwareRouter:
    """
    Routes tasks to the optimal agent and model based on complexity and budget.

    Features:
    - Token-based complexity estimation
    - Tiered model selection with cost awareness
    - Per-task budget enforcement
    - Early exit when confidence is high
    """

    def __init__(self, default_budget: float = 0.10) -> None:
        """
        Args:
            default_budget: Maximum USD budget per task (default $0.10).
        """
        self.default_budget = default_budget

    def estimate_complexity(self, task: str) -> ComplexityTier:
        """
        Estimate the complexity tier of a task string.

        Heuristic: longer + more question marks + more technical keywords = higher complexity.
        """
        word_count = len(task.split())
        has_technical = any(
            kw in task.lower()
            for kw in ("code", "debug", "architecture", "implement", "analyze", "deploy", "optimize")
        )
        has_multiple_steps = task.count("\n") > 2 or task.count(".") > 3

        if word_count < 20 and not has_technical:
            return ComplexityTier.LOW
        if word_count < 60 and not has_multiple_steps:
            return ComplexityTier.MEDIUM
        if word_count < 150 or has_technical:
            return ComplexityTier.HIGH
        return ComplexityTier.VERY_HIGH

    def _estimate_tokens(self, task: str) -> int:
        """Rough token estimate: ~1.3 tokens per word for English text."""
        return int(len(task.split()) * 1.3) + 50  # +50 for system prompt overhead

    def select_model(self, tier: ComplexityTier, budget: float | None = None) -> str:
        """
        Select a model for the given complexity tier, respecting the budget.

        Falls back to a cheaper model if the tier's default exceeds the budget.
        """
        budget = budget or self.default_budget
        preferred_model = TIER_MODEL_MAP[tier]
        preferred_cost_input = MODEL_COST_MAP[preferred_model]["input"]

        if preferred_cost_input <= budget / 2:
            return preferred_model

        # Degrade to the cheapest feasible model
        for fallback_tier in ComplexityTier:
            model = TIER_MODEL_MAP[fallback_tier]
            if MODEL_COST_MAP[model]["input"] <= budget / 2:
                logger.info("Budget %.4f too low for %s; falling back to %s", budget, preferred_model, model)
                return model

        return TIER_MODEL_MAP[ComplexityTier.LOW]

    def route(self, task: str, agent_type: str, budget: float | None = None) -> RoutingDecision:
        """
        Make a full routing decision for the given task.

        Args:
            task: The user's task/prompt.
            agent_type: The target agent archetype (e.g., "react", "debate").
            budget: Optional per-task budget override.

        Returns:
            A RoutingDecision with the selected model, cost estimate, and remaining budget.
        """
        budget = budget or self.default_budget
        tier = self.estimate_complexity(task)
        model = self.select_model(tier, budget)
        estimated_tokens = self._estimate_tokens(task)
        input_cost = estimated_tokens / 1000 * MODEL_COST_MAP[model]["input"]
        output_cost = (estimated_tokens * 1.5) / 1000 * MODEL_COST_MAP[model]["output"]
        total_cost = input_cost + output_cost

        return RoutingDecision(
            agent_type=agent_type,
            model=model,
            tier=tier,
            estimated_input_tokens=estimated_tokens,
            estimated_cost=round(total_cost, 6),
            budget_remaining=round(budget - total_cost, 6),
        )
