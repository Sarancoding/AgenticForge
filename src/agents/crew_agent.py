"""
CrewAgent — hierarchical agent teams inspired by CrewAI patterns.

Manages a crew of agents with a manager that decomposes tasks,
assigns them to specialist agents, and synthesizes results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class CrewMember:
    """An individual agent in the crew."""

    name: str
    role: str
    expertise: list[str]
    llm_call: Callable[[str], str] | None = None


@dataclass
class CrewTask:
    """A task assigned to a crew member."""

    agent_name: str
    description: str
    subtasks: list[str] = field(default_factory=list)
    result: str = ""
    status: str = "pending"


@dataclass
class CrewResult:
    """Result of a crew execution."""

    final_output: str
    tasks: list[CrewTask] = field(default_factory=list)
    manager_notes: str = ""


class CrewAgent:
    """
    Hierarchical crew of agents with a manager for task decomposition.

    Flow:
    1. Manager receives a complex task.
    2. Manager decomposes into subtasks and assigns to specialists.
    3. Specialists execute subtasks in parallel.
    4. Manager synthesizes results into final output.
    """

    def __init__(
        self,
        manager_llm: Callable[[str], str] | None = None,
    ) -> None:
        self._members: dict[str, CrewMember] = {}
        self._manager_llm = manager_llm or (lambda p: f"[Manager: {p[:60]}...]")
        self._default_llm = lambda p: f"[Crew: {p[:60]}...]"

    def add_member(self, name: str, role: str, expertise: list[str] | None = None,
                   llm_call: Callable[[str], str] | None = None) -> None:
        """Add a specialist agent to the crew."""
        self._members[name] = CrewMember(
            name=name,
            role=role,
            expertise=expertise or [],
            llm_call=llm_call or self._default_llm,
        )
        logger.info("Crew member added: %s (%s)", name, role)

    def remove_member(self, name: str) -> None:
        self._members.pop(name, None)

    def _decompose(self, task: str) -> list[str]:
        """Manager decomposes a task into subtasks."""
        decomposition = self._manager_llm(
            f"Decompose this task into 2-4 specific subtasks:\n{task}\n\n"
            f"Subtask 1:"
        )
        # Parse numbered subtasks
        subtasks = []
        for line in decomposition.strip().split("\n"):
            line = line.strip()
            if line and any(line.startswith(f"{i}.") or line.startswith(f"{i}:") for i in range(1, 10)):
                clean = line.split(".", 1)[-1].split(":", 1)[-1].strip() if "." in line or ":" in line else line
                subtasks.append(clean)
        return subtasks[:4] or ["Execute the task as described."]

    def _assign(self, subtask: str) -> str:
        """Assign a subtask to the best-suited crew member."""
        for name, member in self._members.items():
            if any(exp in subtask.lower() for exp in member.expertise):
                llm = member.llm_call or self._default_llm
                return llm(f"As {member.role}, handle this subtask:\n{subtask}")
        # Fallback to first member
        if self._members:
            first = next(iter(self._members.values()))
            llm = first.llm_call or self._default_llm
            return llm(f"Handle this subtask:\n{subtask}")
        return f"[No crew members available for: {subtask}]"

    def _synthesize(self, task: str, task_results: list[CrewTask]) -> str:
        """Manager synthesizes individual results into final output."""
        summary = "\n".join(
            f"{t.agent_name}: {t.result[:200]}" for t in task_results if t.result
        )
        return self._manager_llm(
            f"Original task: {task}\n\n"
            f"Results from specialists:\n{summary}\n\n"
            f"Synthesize these into a cohesive final output."
        )

    def execute(self, task: str) -> CrewResult:
        """
        Execute a task with the crew.

        Args:
            task: The complex task to decompose and execute.

        Returns:
            CrewResult with full task trace.
        """
        # 1. Decompose
        subtask_descriptions = self._decompose(task)
        tasks: list[CrewTask] = []

        # 2. Assign and execute
        for desc in subtask_descriptions:
            agent_name = "manager"
            result = self._assign(desc)
            tasks.append(CrewTask(
                agent_name=agent_name,
                description=desc,
                result=result,
                status="completed",
            ))

        # 3. Synthesize
        final = self._synthesize(task, tasks)
        return CrewResult(final_output=final, tasks=tasks,
                          manager_notes=f"Crew executed with {len(self._members)} members across {len(subtask_descriptions)} subtasks")

    @property
    def member_count(self) -> int:
        return len(self._members)
