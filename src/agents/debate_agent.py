"""
Multi-agent debate system — swarm orchestration with proposal generation,
critic evaluation, voting/consensus, and output aggregation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class Proposal:
    """A single proposal from a debater agent."""

    agent_id: int
    content: str
    critic_score: float = 0.0
    votes: int = 0


@dataclass
class DebateResult:
    """The final result of a multi-agent debate."""

    consensus_output: str
    proposals: list[Proposal] = field(default_factory=list)
    winner: Proposal | None = None


class DebateAgent:
    """
    Multi-agent debate system with proposers, a critic, voting, and an aggregator.

    Flow:
    1. N proposer agents each generate an independent solution.
    2. A critic evaluates each proposal against quality criteria.
    3. Weighted voting determines consensus.
    4. An aggregator synthesizes the final output.
    """

    def __init__(
        self,
        num_proposers: int = 3,
        llm_call: Callable[[str], str] | None = None,
    ) -> None:
        """
        Args:
            num_proposers: Number of proposing agents in the swarm.
            llm_call: Function to call the LLM.
        """
        self.num_proposers = num_proposers
        self._llm = llm_call or (lambda p: f"[Proposal for: {p[:60]}...]")

    def generate_proposal(self, agent_id: int, task: str) -> str:
        """Generate a solution proposal from a single agent."""
        return self._llm(
            f"You are Debater #{agent_id}. Propose a solution for this task:\n{task}\n\nProposal:"
        )

    def critique(self, proposal: Proposal, task: str) -> float:
        """
        Evaluate a proposal and return a score (0.0 to 10.0).
        """
        score_raw = self._llm(
            f"Task: {task}\nProposal: {proposal.content}\n"
            f"Rate this proposal (0-10) on correctness, efficiency, and safety.\nScore:"
        )
        try:
            score = float(score_raw.strip())
        except (ValueError, TypeError):
            score = 5.0
        return min(max(score, 0.0), 10.0)

    def aggregate(self, proposals: list[Proposal], task: str) -> str:
        """Synthesize the final output from the highest-scored proposals."""
        top = sorted(proposals, key=lambda p: p.critic_score, reverse=True)[:2]
        combined = "\n\n---\n\n".join(f"Option {i+1}: {p.content}" for i, p in enumerate(top))
        return self._llm(
            f"Task: {task}\n\nBelow are the top proposals from the debate.\n"
            f"Synthesize the best combined solution:\n\n{combined}\n\nFinal Solution:"
        )

    def debate(self, task: str) -> DebateResult:
        """
        Run the full multi-agent debate process.

        Args:
            task: The problem statement for debate.

        Returns:
            DebateResult with the consensus output and all proposals.
        """
        proposals: list[Proposal] = []

        # 1. Generate proposals
        for agent_id in range(1, self.num_proposers + 1):
            content = self.generate_proposal(agent_id, task)
            proposals.append(Proposal(agent_id=agent_id, content=content))

        # 2. Critique
        for proposal in proposals:
            score = self.critique(proposal, task)
            proposal.critic_score = score

        # 3. Voting (score-weighted)
        total_score = sum(p.critic_score for p in proposals) or 1.0
        for proposal in proposals:
            proposal.votes = int((proposal.critic_score / total_score) * 100)

        # 4. Aggregate
        winners = sorted(proposals, key=lambda p: p.critic_score, reverse=True)
        winner = winners[0] if winners else None
        consensus = self.aggregate(proposals, task)

        return DebateResult(consensus_output=consensus, proposals=proposals, winner=winner)
