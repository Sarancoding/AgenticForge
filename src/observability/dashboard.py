"""
Observability dashboard panels — reusable Streamlit components for
displaying metrics, traces, alerts, and canary results.
"""

from __future__ import annotations

from typing import Any


def render_metrics_panel(metrics_summary: dict) -> str:
    """
    Generate a markdown summary of current metrics for the Streamlit UI.
    """
    lat = metrics_summary.get("latency_ms", {})
    lines = [
        "## 📊 Live Metrics Dashboard",
        "",
        "### Latency",
        f"- **p50**: {lat.get('p50', 0):.0f} ms",
        f"- **p95**: {lat.get('p95', 0):.0f} ms",
        f"- **p99**: {lat.get('p99', 0):.0f} ms",
        "",
        "### Cost",
        f"- **Avg per task**: ${metrics_summary.get('avg_cost_usd', 0):.5f}",
        f"- **Total (window)**: ${metrics_summary.get('total_cost_usd', 0):.4f}",
        "",
        "### Reliability",
        f"- **Success rate**: {metrics_summary.get('success_rate', 1.0):.1%}",
        f"- **Throughput**: {metrics_summary.get('throughput_rps', 0):.2f} req/s",
        f"- **Total executions**: {metrics_summary.get('total_snapshots', 0)}",
        f"- **Excessive loops**: {metrics_summary.get('excessive_loops', 0)}",
    ]
    return "\n".join(lines)


def render_cost_breakdown(metrics_summary: dict) -> str:
    """Generate a cost analytics markdown panel."""
    return (
        f"## 💰 Cost Analytics\n\n"
        f"| Metric | Value |\n"
        f"|---|---|\n"
        f"| Avg Cost/Task | ${metrics_summary.get('avg_cost_usd', 0):.5f} |\n"
        f"| Total Cost (Window) | ${metrics_summary.get('total_cost_usd', 0):.4f} |\n"
        f"| Budget Remaining | ${max(0, 1.0 - metrics_summary.get('total_cost_usd', 0)):.4f} |\n"
    )


def render_alerts_panel(alerts: list) -> str:
    """Generate an alerts display panel."""
    if not alerts:
        return "### ✅ No Active Alerts\n\nAll systems operational."

    lines = ["### 🚨 Active Alerts", ""]
    for i, alert in enumerate(alerts[-10:]):  # Last 10
        severity_icon = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }.get(getattr(alert, "severity", None) and alert.severity.value, "⚪")
        lines.append(f"{severity_icon} **[{alert.severity.value.upper()}]** {alert.rule_name}")
        lines.append(f"   {alert.message}")
        lines.append(f"   _{alert.timestamp}_")
        lines.append("")
    return "\n".join(lines)


def render_canary_panel(canary_results: list[dict]) -> str:
    """Generate a canary testing results panel."""
    if not canary_results:
        return "### 🧪 No Active Canaries"

    lines = ["### 🧪 Canary Tests", ""]
    for result in canary_results:
        status = "✅" if result.get("passed") else "❌"
        lines.append(f"{status} **{result.get('candidate_name', 'unknown')}**")
        lines.append(f"   Requests: {result.get('total_requests', 0)}")
        lines.append(f"   Latency: {result.get('avg_latency_ms', 0):.0f}ms")
        lines.append(f"   Reason: {result.get('reason', 'N/A')}")
        lines.append("")
    return "\n".join(lines)
