"""
Unified tracing manager — supports LangSmith (RunTree) and
Arize/Phoenix (OpenTelemetry) for distributed tracing of agent
executions, LLM calls, and tool invocations.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TracerManager:
    """
    Unified tracer that bridges LangSmith and Arize/Phoenix instrumentation.

    Features:
    - Auto-detects available providers from environment variables.
    - Creates nested spans for agent → tool → LLM call hierarchies.
    - Attaches token counts, latency, costs, and custom metadata.
    - Supports manual tracing via context manager or decorator.
    """

    def __init__(self, service_name: str = "nexuscore") -> None:
        self.service_name = service_name
        self._langsmith_enabled = bool(os.environ.get("LANGSMITH_API_KEY"))
        self._phoenix_enabled = bool(os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"))
        self._provider = "none"

        if self._langsmith_enabled:
            self._provider = "langsmith"
            self._init_langsmith()
        elif self._phoenix_enabled:
            self._provider = "phoenix"
            self._init_phoenix()
        else:
            logger.info("No tracing provider configured. Using null tracer.")

        logger.info("Tracer initialized — provider=%s", self._provider)

    def _init_langsmith(self) -> None:
        """Initialize LangSmith tracing."""
        try:
            from langsmith.run_trees import RunTree  # type: ignore[import-untyped]
            self._RunTree = RunTree
        except ImportError:
            logger.warning("langsmith not installed. Run: pip install langsmith")
            self._provider = "none"

    def _init_phoenix(self) -> None:
        """Initialize Arize/Phoenix OpenTelemetry tracing."""
        try:
            from phoenix.otel import register  # type: ignore[import-untyped]
            register(
                endpoint=os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
            )
            from opentelemetry import trace  # type: ignore[import-untyped]
            self._otel_tracer = trace.get_tracer(self.service_name)
            self._SpanAttributes = None
            try:
                from phoenix.otel import SpanAttributes  # type: ignore[import-untyped]
                self._SpanAttributes = SpanAttributes
            except ImportError:
                pass
        except ImportError:
            logger.warning("arize-phoenix not installed. Run: pip install arize-phoenix")
            self._provider = "none"

    @property
    def provider(self) -> str:
        return self._provider

    @contextmanager
    def trace(
        self,
        name: str,
        span_type: str = "chain",
        inputs: dict | None = None,
        metadata: dict | None = None,
    ):
        """
        Context manager for tracing a span of execution.

        Args:
            name: Span name (e.g., "agent.react", "tool.search_web").
            span_type: Type of span (chain, tool, llm, retriever).
            inputs: Input data to attach to the span.
            metadata: Custom key-value metadata.

        Yields:
            Span context object for attaching outputs, token counts, etc.
        """
        trace_id = str(uuid4())
        context = TraceSpanContext(
            trace_id=trace_id,
            name=name,
            provider=self._provider,
        )

        if self._provider == "langsmith":
            with self._langsmith_span(name, span_type, inputs, metadata, context):
                yield context
        elif self._provider == "phoenix":
            with self._phoenix_span(name, inputs, metadata, context):
                yield context
        else:
            # Null tracer — just log
            logger.debug("[trace:%s] %s (no provider)", trace_id[:8], name)
            yield context

    def _langsmith_span(self, name, span_type, inputs, metadata, context):
        """Create a LangSmith RunTree span."""
        try:
            run = self._RunTree(
                name=name,
                run_type=span_type,
                inputs=inputs or {},
                extra={"metadata": metadata or {}},
            )
            # For nested spans, would use run.create_child(...)
            context._langsmith_run = run
            yield
            run.end(outputs=context._outputs)
            if context._usage:
                run.usage_metadata = context._usage
            run.post()
        except Exception as exc:
            logger.warning("LangSmith trace failed: %s", exc)
            yield

    def _phoenix_span(self, name, inputs, metadata, context):
        """Create an OpenTelemetry span via Phoenix."""
        try:
            attrs = {}
            if self._SpanAttributes:
                if inputs:
                    attrs[self._SpanAttributes.INPUT_VALUE] = str(inputs)
            if metadata:
                attrs.update(metadata)

            with self._otel_tracer.start_as_current_span(name, attributes=attrs) as span:
                context._otel_span = span
                yield
                if context._usage:
                    span.set_attribute("llm.token_count.total", context._usage.get("total_tokens", 0))
                    span.set_attribute("llm.token_count.prompt", context._usage.get("input_tokens", 0))
                    span.set_attribute("llm.token_count.completion", context._usage.get("output_tokens", 0))
                    if "cost" in (metadata or {}):
                        span.set_attribute("llm.usage.total_cost", metadata["cost"])
                if context._outputs:
                    span.set_attribute("output.value", str(context._outputs))
        except Exception as exc:
            logger.warning("Phoenix trace failed: %s", exc)
            yield

    def flatten_dict(self, d: dict, parent_key: str = "") -> dict:
        """Flatten nested dict into dot-separated keys for metadata."""
        items: list = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)


class TraceSpanContext:
    """Context object passed within a traced span."""

    def __init__(self, trace_id: str, name: str, provider: str) -> None:
        self.trace_id = trace_id
        self.name = name
        self.provider = provider
        self._outputs: dict | None = None
        self._usage: dict | None = None
        self._langsmith_run = None
        self._otel_span = None

    def set_output(self, outputs: dict) -> None:
        self._outputs = outputs

    def set_usage(self, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0) -> None:
        self._usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens or input_tokens + output_tokens,
        }
