"""
FastAPI middleware for automatic observability — traces every request,
collects latency/cost metrics, and triggers alert evaluation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import MetricsCollector
from .alerting import AlertEngine
from .tracer import TracerManager

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that instruments every HTTP request with:
    - Distributed tracing (LangSmith/Phoenix)
    - Latency metrics collection
    - Token usage tracking
    - Cost estimation
    - Automatic alert evaluation
    """

    def __init__(
        self,
        app: Any,
        tracer: TracerManager | None = None,
        metrics: MetricsCollector | None = None,
        alerts: AlertEngine | None = None,
    ) -> None:
        super().__init__(app)
        self.tracer = tracer or TracerManager()
        self.metrics = metrics or MetricsCollector()
        self.alerts = alerts or AlertEngine()

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Trace the request, record metrics, and check alerts."""
        path = request.url.path
        method = request.method

        # Skip health/metrics endpoints to avoid observation loop
        if path in ("/health", "/metrics", "/api/observability/metrics"):
            return await call_next(request)

        start = time.monotonic()
        span_name = f"{method} {path}"

        with self.tracer.trace(span_name, span_type="chain", inputs={"path": path}) as span:
            try:
                response = await call_next(request)

                elapsed_ms = (time.monotonic() - start) * 1000
                self.metrics.record_latency("http", elapsed_ms)

                if response.status_code < 400:
                    self.metrics.record_success("http")
                else:
                    self.metrics.record_failure("http", f"HTTP {response.status_code}")

                span.set_output({
                    "status_code": response.status_code,
                    "latency_ms": round(elapsed_ms, 2),
                })

                # Evaluate alerts periodically
                if self.metrics.total_executions % 10 == 0:
                    summary = self.metrics.summary()
                    fired = self.alerts.evaluate(summary)
                    if fired:
                        logger.info("%d alert(s) fired on %s", len(fired), path)

                return response

            except Exception as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                self.metrics.record_failure("http", str(exc))
                raise
