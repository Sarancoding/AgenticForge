"""
Event-triggered automation agent — webhook/queue listeners, idempotent
workflow execution, dead-letter handling, and robust retry logic.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EventStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class Event:
    """A work event for the automation agent."""

    id: str
    payload: dict
    status: EventStatus = EventStatus.PENDING
    retries: int = 0
    max_retries: int = 3
    error: str | None = None


@dataclass
class EventResult:
    """Result of processing an event."""

    event_id: str
    success: bool
    output: str | None = None
    error: str | None = None
    processing_time: float = 0.0


class EventAgent:
    """
    Event-triggered automation agent that listens for webhooks/queue messages
    and executes workflows with idempotency, retry, and dead-letter handling.

    Features:
    - Idempotent execution (event ID deduplication)
    - Exponential backoff retry (1s, 2s, 4s, 8s…)
    - Configurable max retries
    - Dead-letter queue for permanently failed events
    """

    def __init__(
        self,
        workflow_handler: Callable[[dict], str] | None = None,
        max_retries: int = 3,
    ) -> None:
        """
        Args:
            workflow_handler: Async callable that processes an event payload.
            max_retries: Maximum retry attempts before dead-letter.
        """
        self._workflow = workflow_handler or (lambda p: f"Processed: {p}")
        self.max_retries = max_retries
        self._processed_ids: set[str] = set()
        self._dead_letter_queue: list[Event] = []
        self._event_log: dict[str, Event] = {}

    def _get_backoff_delay(self, retry: int) -> float:
        """Exponential backoff: 1s, 2s, 4s, 8s... capped at 60s."""
        return min(2 ** retry, 60.0)

    async def process_event(self, event: Event) -> EventResult:
        """
        Process a single event with idempotency check and retry logic.

        Args:
            event: The event to process.

        Returns:
            EventResult indicating success/failure.
        """
        # Idempotency check
        if event.id in self._processed_ids:
            logger.info("Duplicate event %s — skipping.", event.id)
            return EventResult(event_id=event.id, success=True, output="Duplicate — already processed.")

        start_time = time.monotonic()
        last_error: str | None = None

        for attempt in range(event.max_retries + 1):
            try:
                event.status = EventStatus.PROCESSING
                output = self._workflow(event.payload)
                event.status = EventStatus.COMPLETED
                self._processed_ids.add(event.id)
                self._event_log[event.id] = event

                elapsed = time.monotonic() - start_time
                logger.info("Event %s processed in %.2fs (attempt %d).", event.id, elapsed, attempt + 1)
                return EventResult(
                    event_id=event.id,
                    success=True,
                    output=output,
                    processing_time=round(elapsed, 3),
                )

            except Exception as exc:
                last_error = str(exc)
                event.retries = attempt + 1
                logger.warning(
                    "Event %s attempt %d failed: %s", event.id, attempt + 1, last_error
                )

                if attempt < event.max_retries:
                    delay = self._get_backoff_delay(attempt)
                    logger.info("Retrying event %s in %.1fs...", event.id, delay)
                    await asyncio.sleep(delay)

        # Exhausted retries — move to dead-letter
        event.status = EventStatus.DEAD_LETTER
        event.error = last_error
        self._dead_letter_queue.append(event)
        self._event_log[event.id] = event

        elapsed = time.monotonic() - start_time
        logger.error("Event %s moved to dead-letter after %d retries.", event.id, event.max_retries)
        return EventResult(
            event_id=event.id,
            success=False,
            error=last_error,
            processing_time=round(elapsed, 3),
        )

    async def process_events(self, events: list[Event]) -> list[EventResult]:
        """Process multiple events concurrently."""
        tasks = [self.process_event(event) for event in events]
        return await asyncio.gather(*tasks)

    def get_dead_letter_queue(self) -> list[Event]:
        """Return all events that have been dead-lettered."""
        return list(self._dead_letter_queue)

    def create_event(self, payload: dict) -> Event:
        """Create a new event with a unique ID."""
        return Event(
            id=str(uuid.uuid4()),
            payload=payload,
            max_retries=self.max_retries,
        )
