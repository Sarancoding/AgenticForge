"""
Observability package for NexusCore — tracing, metrics, alerting,
canary testing, rollback, and dashboard for enterprise-grade operations.
"""

from .tracer import TracerManager
from .metrics import MetricsCollector
from .alerting import AlertEngine, AlertRule, AlertSeverity
from .canary import CanaryTester, CanaryResult
from .rollback import RollbackManager
from .middleware import ObservabilityMiddleware
from .dashboard import render_metrics_panel, render_alerts_panel, render_canary_panel, render_cost_breakdown

__all__ = [
    "TracerManager",
    "MetricsCollector",
    "AlertEngine",
    "AlertRule",
    "AlertSeverity",
    "CanaryTester",
    "CanaryResult",
    "RollbackManager",
    "ObservabilityMiddleware",
    "render_metrics_panel",
    "render_alerts_panel",
    "render_canary_panel",
    "render_cost_breakdown",
]
