"""
Test cases for the Tool Orchestrator.

Verify dynamic registration, capability-based routing,
parallel execution, and conflict resolution.
"""

import pytest
from src.tools.orchestrator import ToolOrchestrator, Tool


class TestToolOrchestrator:
    """Suite of tests for ToolOrchestrator."""

    def setup_method(self) -> None:
        self.orchestrator = ToolOrchestrator()
        self._register_test_tools()

    def _register_test_tools(self) -> None:
        self.orchestrator.register_tool(
            Tool(name="search_web", description="Search the web",
                 capabilities=["search", "web"], permission_level="user",
                 fn=lambda q: f"Results for: {q}")
        )
        self.orchestrator.register_tool(
            Tool(name="search_db", description="Search the database",
                 capabilities=["search", "database"], permission_level="admin",
                 fn=lambda q: f"DB results for: {q}")
        )
        self.orchestrator.register_tool(
            Tool(name="calculator", description="Math calculations",
                 capabilities=["math"], permission_level="user",
                 fn=lambda expr: str(eval(expr)))  # noqa: S307
        )

    def test_register_tool(self) -> None:
        """Registering a tool should add it to the registry."""
        assert self.orchestrator.tool_count == 3

    def test_duplicate_registration_raises(self) -> None:
        """Registering a tool with a duplicate name should raise ValueError."""
        with pytest.raises(ValueError, match="already registered"):
            self.orchestrator.register_tool(
                Tool(name="search_web", description="Duplicate",
                     capabilities=["search"], fn=lambda: "")
            )

    def test_find_by_capability(self) -> None:
        """Finding tools by capability should return all matching tools."""
        tools = self.orchestrator.find_tools_by_capability("search")
        assert len(tools) == 2, f"Expected 2 search tools, got {len(tools)}"

    def test_conflict_resolution_prefers_admin(self) -> None:
        """When two tools claim the same capability, admin-level should win."""
        tools = self.orchestrator.find_tools_by_capability("search")
        winner = self.orchestrator.resolve_conflict(tools, "search for records")
        assert winner.name == "search_db", f"Expected search_db, got {winner.name}"

    def test_execute_tool_success(self) -> None:
        """Executing a registered tool should return a successful result."""
        result = self.orchestrator.execute_tool("calculator", expression="2+2")
        assert result.success is True
        assert result.output == "4"

    def test_execute_tool_not_found(self) -> None:
        """Executing an unregistered tool should return an error result."""
        result = self.orchestrator.execute_tool("nonexistent")
        assert result.success is False
        assert "not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_parallel_execution(self) -> None:
        """Multiple tools should execute in parallel."""
        calls = [
            ("calculator", {"expression": "1+1"}),
            ("search_web", {"q": "hello"}),
        ]
        results = await self.orchestrator.execute_parallel(calls)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_unregister_tool(self) -> None:
        """Unregistering a tool should remove it from the registry."""
        self.orchestrator.unregister_tool("calculator")
        assert self.orchestrator.tool_count == 2
        assert self.orchestrator.get_tool("calculator") is None

    def test_list_tools_metadata(self) -> None:
        """List tools should return all tool metadata."""
        tools = self.orchestrator.list_tools()
        assert len(tools) == 3
        tool_names = [t["name"] for t in tools]
        assert "search_web" in tool_names
        assert "search_db" in tool_names
        assert "calculator" in tool_names
