"""
Hybrid memory manager — merges short-term buffer with long-term
vector recall for context-aware, cross-session conversations.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """A single memory entry with scoring metadata."""

    content: str
    timestamp: float
    importance: float = 1.0
    session_id: str = "default"
    embedding: list[float] | None = None


@dataclass
class MemoryQueryResult:
    """Result of a memory recall query."""

    items: list[MemoryItem] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    query: str = ""


class HybridMemory:
    """
    Two-tier hybrid memory system:

    - **Short-Term Buffer**: Sliding window of recent conversation turns (FIFO).
      Fast recall for immediate context.

    - **Long-Term Vector Recall**: Semantic similarity search over stored
      memory items. Cross-session persistence via a pluggable vector DB interface.

    Relevance scoring combines recency decay, semantic similarity,
    and explicit importance weighting.
    """

    def __init__(
        self,
        short_term_capacity: int = 20,
        decay_rate: float = 0.1,
    ) -> None:
        """
        Args:
            short_term_capacity: Number of recent items to keep in the buffer.
            decay_rate: Time decay factor (0 = no decay, 1 = full decay per step).
        """
        self.short_term_capacity = short_term_capacity
        self.decay_rate = decay_rate
        self._short_term: deque[MemoryItem] = deque(maxlen=short_term_capacity)
        self._long_term: list[MemoryItem] = []

    # ─── Vector DB Interface (pluggable) ──────────────────────────────

    def _compute_embedding(self, text: str) -> list[float]:
        """
        Compute an embedding for the given text.

        Override this method to plug in a real embedding model
        (e.g., OpenAI embeddings, sentence-transformers).
        """
        # Stub: returns a pseudo-embedding for testing
        return [hash(text) % 1000 / 1000.0] * 128

    def _similarity(self, query_embedding: list[float], item_embedding: list[float]) -> float:
        """Cosine similarity between two embeddings."""
        dot = sum(a * b for a, b in zip(query_embedding, item_embedding, strict=False))
        norm_q = sum(a * a for a in query_embedding) ** 0.5 or 1.0
        norm_i = sum(b * b for b in item_embedding) ** 0.5 or 1.0
        return dot / (norm_q * norm_i)

    # ─── Public API ──────────────────────────────────────────────────

    def add(self, content: str, importance: float = 1.0, session_id: str = "default") -> None:
        """
        Add a memory item to both short-term buffer and long-term store.

        Args:
            content: The text content to remember.
            importance: Explicit importance weight (0.0 to 1.0).
            session_id: Session identifier for cross-session filtering.
        """
        import time

        timestamp = time.time()
        embedding = self._compute_embedding(content)

        item = MemoryItem(
            content=content,
            timestamp=timestamp,
            importance=min(max(importance, 0.0), 1.0),
            session_id=session_id,
            embedding=embedding,
        )

        self._short_term.append(item)
        self._long_term.append(item)
        logger.debug("Memory added: %.40s... (importance=%.1f)", content, importance)

    def recall_short_term(self, limit: int | None = None) -> list[MemoryItem]:
        """
        Retrieve the most recent items from the short-term buffer.

        Args:
            limit: Max number of items to return (default: all).

        Returns:
            List of memory items, most recent first.
        """
        items = list(self._short_term)
        items.reverse()
        if limit:
            items = items[:limit]
        return items

    def recall_long_term(self, query: str, top_k: int = 5, session_id: str | None = None) -> MemoryQueryResult:
        """
        Semantic recall from long-term vector store.

        Args:
            query: Natural-language query to match against.
            top_k: Maximum number of results.
            session_id: Optional filter by session.

        Returns:
            MemoryQueryResult with scored items.
        """
        if not self._long_term:
            return MemoryQueryResult(query=query)

        query_embedding = self._compute_embedding(query)

        import time

        now = time.time()
        scored: list[tuple[MemoryItem, float]] = []

        for item in self._long_term:
            if session_id and item.session_id != session_id:
                continue

            # Combined relevance score
            semantic_score = self._similarity(query_embedding, item.embedding or []) if item.embedding else 0.0
            recency_score = max(0.0, 1.0 - (now - item.timestamp) * self.decay_rate)
            importance_score = item.importance

            combined = 0.5 * semantic_score + 0.3 * recency_score + 0.2 * importance_score
            scored.append((item, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_items = scored[:top_k]

        return MemoryQueryResult(
            items=[item for item, _ in top_items],
            scores=[score for _, score in top_items],
            query=query,
        )

    def search(self, query: str, top_k: int = 5, session_id: str | None = None) -> MemoryQueryResult:
        """
        Unified recall — combines short-term and long-term results.

        Args:
            query: Natural-language query.
            top_k: Maximum results.
            session_id: Optional session filter.

        Returns:
            Ranked and scored memory results.
        """
        short_term = self.recall_short_term(limit=top_k)
        long_term_result = self.recall_long_term(query, top_k=top_k, session_id=session_id)

        # Merge — prefer long-term (semantic) matches, supplement with short-term
        seen_ids = {id(item) for item in long_term_result.items}
        merged = list(long_term_result.items)

        for item in short_term:
            if id(item) not in seen_ids:
                merged.append(item)
                seen_ids.add(id(item))

        return MemoryQueryResult(items=merged[:top_k], query=query)

    def clear_session(self, session_id: str) -> int:
        """
        Clear all memory items for a given session.

        Args:
            session_id: The session to clear.

        Returns:
            Number of items removed.
        """
        before = len(self._long_term)
        self._long_term = [item for item in self._long_term if item.session_id != session_id]
        # Also clean short-term
        self._short_term = deque(
            (item for item in self._short_term if item.session_id != session_id),
            maxlen=self.short_term_capacity,
        )
        removed = before - len(self._long_term)
        logger.info("Cleared %d memory items for session %s.", removed, session_id)
        return removed
