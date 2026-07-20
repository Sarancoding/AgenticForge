"""
Dynamic tool orchestration — registration, capability-based routing,
parallel execution, and conflict resolution.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """A registered tool with metadata."""

    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    permission_level: str = "user"  # "user", "admin", "system"
    fn: Callable[..., Any] | None = None


@dataclass
class ToolResult:
    """Result of executing a tool."""

    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None


class ToolOrchestrator:
    """
    Manages a dynamic tool registry with capability-based routing,
    parallel execution, and conflict resolution.

    Features:
    - Tools register by name, capabilities, and permission level.
    - Task-to-tool matching by capability tags.
    - Independent tools run concurrently via asyncio.gather.
    - Conflict resolution: highest confidence/priority tool wins.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool in the orchestrator.

        Args:
            tool: The Tool to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool
        logger.info("Tool registered: %s (%s)", tool.name, ", ".join(tool.capabilities))

    def unregister_tool(self, name: str) -> None:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            logger.info("Tool unregistered: %s", name)

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def find_tools_by_capability(self, capability: str) -> list[Tool]:
        """Find all tools that match a given capability tag."""
        return [t for t in self._tools.values() if capability in t.capabilities]

    def resolve_conflict(self, tools: list[Tool], task: str) -> Tool:
        """
        Resolve a conflict when multiple tools claim the same capability.

        Resolution strategy: prefer admin-level tools, then by description
        relevance to the task, then alphabetically.
        """
        # Prefer higher permission level
        permission_order = {"system": 0, "admin": 1, "user": 2}
        sorted_tools = sorted(
            tools,
            key=lambda t: (
                permission_order.get(t.permission_level, 99),
                -sum(word in task.lower() for word in t.description.lower().split()),
                t.name,
            ),
        )
        return sorted_tools[0]

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Execute a single tool by name.

        Args:
            tool_name: Name of the registered tool.
            **kwargs: Arguments to pass to the tool function.

        Returns:
            ToolResult with success status and output/error.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(tool_name=tool_name, success=False, error=f"Tool '{tool_name}' not found.")
        if not tool.fn:
            return ToolResult(tool_name=tool_name, success=False, error=f"Tool '{tool_name}' has no callable.")

        try:
            if asyncio.iscoroutinefunction(tool.fn):
                output = await tool.fn(**kwargs)
            else:
                output = tool.fn(**kwargs)
            logger.info("Tool %s executed successfully.", tool_name)
            return ToolResult(tool_name=tool_name, success=True, output=output)
        except Exception as exc:
            logger.error("Tool %s failed: %s", tool_name, exc)
            return ToolResult(tool_name=tool_name, success=False, error=str(exc))

    async def execute_parallel(self, tool_calls: list[tuple[str, dict]]) -> list[ToolResult]:
        """
        Execute multiple tools in parallel.

        Args:
            tool_calls: List of (tool_name, kwargs) tuples.

        Returns:
            List of ToolResult objects in the same order as input.
        """
        tasks = [self.execute_tool(name, **kwargs) for name, kwargs in tool_calls]
        return await asyncio.gather(*tasks)

    def route_task(self, task: str, required_capability: str) -> list[Tool]:
        """
        Route a task to the best tool(s) for a given capability.

        Args:
            task: The task description.
            required_capability: The capability needed.

        Returns:
            List of matching tools (conflict-resolved).
        """
        matching = self.find_tools_by_capability(required_capability)
        if not matching:
            logger.warning("No tools found for capability '%s'.", required_capability)
            return []

        if len(matching) == 1:
            return [matching[0]]

        # Conflict resolution
        best = self.resolve_conflict(matching, task)
        logger.info("Resolved conflict: %s selected from %d candidates.", best.name, len(matching))
        return [best]

    @property
    def tool_count(self) -> int:
        """Number of registered tools."""
        return len(self._tools)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with their metadata."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "capabilities": t.capabilities,
                "permission_level": t.permission_level,
            }
            for t in self._tools.values()
        ]
