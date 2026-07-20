"""
Test cases for Hybrid Memory.

Verify that short-term buffer and long-term vector recall work correctly,
and that relevance scoring ranks items appropriately.
"""

from src.memory.memory_manager import HybridMemory


class TestHybridMemory:
    """Suite of tests for HybridMemory."""

    def setup_method(self) -> None:
        self.memory = HybridMemory(short_term_capacity=5)

    def test_add_and_short_term_recall(self) -> None:
        """Items added to memory should be retrievable from short-term buffer."""
        self.memory.add("Hello, world!", importance=0.5)
        items = self.memory.recall_short_term()
        assert len(items) == 1
        assert items[0].content == "Hello, world!"

    def test_short_term_capacity(self) -> None:
        """Short-term buffer should respect its capacity limit (FIFO)."""
        for i in range(10):
            self.memory.add(f"Item {i}", importance=0.1)
        items = self.memory.recall_short_term()
        assert len(items) == 5, f"Expected 5 items, got {len(items)}"
        assert items[0].content == "Item 9"  # Most recent first

    def test_long_term_vector_recall(self) -> None:
        """Long-term recall should find semantically similar items."""
        self.memory.add("The capital of France is Paris.", importance=0.9)
        self.memory.add("Python is a programming language.", importance=0.7)
        self.memory.add("The sky is blue.", importance=0.3)

        result = self.memory.recall_long_term("Tell me about France", top_k=2)
        assert len(result.items) > 0
        # The France-related item should be among the top results
        contents = [item.content for item in result.items]
        assert any("France" in c for c in contents), f"Expected France-related results, got {contents}"

    def test_clear_session(self) -> None:
        """Clearing a session should remove all its items."""
        self.memory.add("Session 1 data", importance=0.5, session_id="session_1")
        self.memory.add("Session 2 data", importance=0.5, session_id="session_2")

        removed = self.memory.clear_session("session_1")
        assert removed > 0, "Expected items to be removed"

        result = self.memory.recall_long_term("data", top_k=10)
        contents = [item.content for item in result.items]
        assert "Session 2 data" in contents
        assert "Session 1 data" not in contents

    def test_unified_search_combines_tiers(self) -> None:
        """Unified search should return both short-term and long-term results."""
        self.memory.add("A long-term memory item about AI.", importance=0.8)
        result = self.memory.search("artificial intelligence", top_k=5)
        assert len(result.items) > 0
        assert result.query == "artificial intelligence"
