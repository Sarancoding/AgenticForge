"""
Alert engine — configurable rules that trigger on metrics thresholds,
excessive loops, failure spikes, cost anomalies, and latency violations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """A single alert instance."""

    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: str = ""
    status: AlertStatus = AlertStatus.FIRING
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class AlertRule:
    """
    A configurable alert rule.

    Example:
        AlertRule(
            name="high_latency",
            description="Alert when p95 latency exceeds threshold",
            severity=AlertSeverity.WARNING,
            check_fn=lambda metrics: metrics.get("latency_ms", {}).get("p95", 0) > 5000,
            message_template="p95 latency is {p95:.0f}ms (threshold: 5000ms)",
        )
    """

    name: str
    description: str
    severity: AlertSeverity
    check_fn: Callable[[dict], bool]
    message_template: str = ""
    cooldown_seconds: int = 300  # Min time between re-firing


class AlertEngine:
    """
    Rule-based alert engine that periodically evaluates metrics
    and fires alerts to registered handlers.

    Built-in rules (auto-registered):
    - excessive_loops: Agent iteration count > threshold
    - high_failure_rate: Success rate < threshold
    - cost_spike: Per-minute cost > threshold
    - high_latency: p95 latency > threshold
    - no_heartbeat: No executions in window
    """

    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._alerts: list[Alert] = []
        self._handlers: list[Callable[[Alert], None]] = []
        self._last_fired: dict[str, float] = {}
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        import time

        def excessive_loops_check(metrics: dict) -> bool:
            return metrics.get("excessive_loops", 0) > 0

        def high_failure_rate_check(metrics: dict) -> bool:
            return metrics.get("success_rate", 1.0) < 0.8

        def high_latency_check(metrics: dict) -> bool:
            return metrics.get("latency_ms", {}).get("p95", 0) > 10000

        def cost_spike_check(metrics: dict) -> bool:
            return metrics.get("total_cost_usd", 0) > 1.0

        def no_heartbeat_check(metrics: dict) -> bool:
            return metrics.get("total_snapshots", 1) == 0

        self.register_rule(AlertRule(
            name="excessive_loops",
            description="Agent exceeded max loop iterations",
            severity=AlertSeverity.WARNING,
            check_fn=excessive_loops_check,
            message_template="Excessive loops detected: {excessive_loops} agents exceeded iteration limit",
        ))
        self.register_rule(AlertRule(
            name="high_failure_rate",
            description="Agent success rate below 80%",
            severity=AlertSeverity.CRITICAL,
            check_fn=high_failure_rate_check,
            message_template="High failure rate: {success_rate:.0%} success (threshold: 80%)",
        ))
        self.register_rule(AlertRule(
            name="high_latency",
            description="p95 latency exceeds 10 seconds",
            severity=AlertSeverity.WARNING,
            check_fn=high_latency_check,
            message_template="High latency: p95={latency_ms[p95]:.0f}ms (threshold: 10000ms)",
        ))
        self.register_rule(AlertRule(
            name="cost_spike",
            description="Total cost exceeds $1.00 in window",
            severity=AlertSeverity.INFO,
            check_fn=cost_spike_check,
            message_template="Cost spike: ${total_cost_usd:.2f} in current window",
        ))
        self.register_rule(AlertRule(
            name="no_heartbeat",
            description="No agent executions detected",
            severity=AlertSeverity.CRITICAL,
            check_fn=no_heartbeat_check,
            message_template="No heartbeat — zero agent executions in the observation window",
        ))

    def register_rule(self, rule: AlertRule) -> None:
        """Register a custom alert rule."""
        self._rules[rule.name] = rule
        logger.info("Alert rule registered: %s (%s)", rule.name, rule.severity.value)

    def unregister_rule(self, name: str) -> None:
        self._rules.pop(name, None)

    def register_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register a callback that fires on each alert."""
        self._handlers.append(handler)

    def evaluate(self, metrics: dict) -> list[Alert]:
        """
        Evaluate all rules against the current metrics snapshot.
        Returns newly fired alerts.
        """
        import time

        new_alerts: list[Alert] = []
        now = time.time()

        for rule in self._rules.values():
            try:
                triggered = rule.check_fn(metrics)
            except Exception as exc:
                logger.warning("Alert rule '%s' check failed: %s", rule.name, exc)
                continue

            if triggered:
                last = self._last_fired.get(rule.name, 0)
                if now - last < rule.cooldown_seconds:
                    continue  # Still in cooldown

                # Format message
                try:
                    message = rule.message_template.format(**metrics)
                except (KeyError, ValueError):
                    message = rule.message_template

                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=message,
                    metadata={"metrics_snapshot": metrics},
                )
                self._alerts.append(alert)
                self._last_fired[rule.name] = now
                new_alerts.append(alert)

                for handler in self._handlers:
                    try:
                        handler(alert)
                    except Exception:
                        logger.exception("Alert handler failed for %s", rule.name)

                logger.log(
                    logging.CRITICAL if rule.severity == AlertSeverity.CRITICAL
                    else logging.WARNING if rule.severity == AlertSeverity.WARNING
                    else logging.INFO,
                    "[ALERT] %s: %s", rule.severity.value.upper(), message,
                )

        return new_alerts

    def acknowledge(self, alert_index: int) -> bool:
        """Mark an alert as acknowledged."""
        if 0 <= alert_index < len(self._alerts):
            self._alerts[alert_index].status = AlertStatus.ACKNOWLEDGED
            return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        """Get all alerts that are still firing."""
        return [a for a in self._alerts if a.status == AlertStatus.FIRING]

    @property
    def recent_alerts(self) -> list[Alert]:
        return self._alerts[-50:]  # Last 50 alerts
