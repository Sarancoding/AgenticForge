#!/usr/bin/env python3
"""
NexusCore Enterprise Benchmark Suite — compares agent patterns
on latency, cost, quality, and convergence.

Usage:
    python demos/benchmark_suite.py
"""

from __future__ import annotations

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.react_agent import ReActAgent
from src.agents.debate_agent import DebateAgent
from src.agents.self_reflective_agent import SelfReflectiveAgent
from src.agents.crew_agent import CrewAgent
from src.agents.workflow_agent import WorkflowAgent


TEST_TASKS = [
    "What is 2+2? Explain in detail.",
    "Write a haiku about artificial intelligence.",
    "List the pros and cons of microservices architecture.",
    "Explain quantum computing to a 10-year-old.",
    "Create a simple project plan for building a mobile app.",
]


def benchmark(func, name: str, tasks: list[str]) -> dict:
    """Run a benchmark on a single agent function."""
    results = {"name": name, "tasks": 0, "total_time_ms": 0.0, "errors": 0}

    for task in tasks:
        try:
            start = time.monotonic()
            func(task)
            elapsed = (time.monotonic() - start) * 1000
            results["tasks"] += 1
            results["total_time_ms"] += elapsed
        except Exception as e:
            results["errors"] += 1
            print(f"   ✗ {name} failed on: {task[:40]}... → {e}")

    results["avg_time_ms"] = results["total_time_ms"] / results["tasks"] if results["tasks"] else 0
    return results


def run_benchmarks():
    """Run all benchmarks and print comparison table."""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       NexusCore Enterprise Benchmark Suite              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nTest tasks: {len(TEST_TASKS)}")
    print(f"Categories: latency, throughput, error rate\n")

    react = ReActAgent(max_iterations=2)
    debate = DebateAgent(num_proposers=2)
    reflective = SelfReflectiveAgent(max_reflections=2)
    crew = CrewAgent()
    crew.add_member("engineer", "Engineer", ["build", "code", "design"])
    workflow = WorkflowAgent()

    benchmarks = [
        ("ReAct Agent", lambda t: react.run(task=t)),
        ("Debate Agent", lambda t: debate.debate(task=t)),
        ("Self-Reflective", lambda t: reflective.reflect(task=t)),
        ("Crew Agent", lambda t: crew.execute(task=t)),
        ("Workflow Agent", lambda t: workflow.run(task=t)),
    ]

    results = []
    for name, func in benchmarks:
        print(f"  Benchmarking {name}...")
        result = benchmark(func, name, TEST_TASKS)
        results.append(result)
        print(f"    ✓ {result['tasks']} tasks in {result['total_time_ms']:.0f}ms")
        if result["errors"]:
            print(f"    ✗ {result['errors']} error(s)")
        print()

    # Results table
    print("\n" + "─" * 60)
    print(f"{'Agent Pattern':<25} {'Avg Time':<12} {'Errors':<8} {'Tasks':<8}")
    print("─" * 60)
    for r in sorted(results, key=lambda x: x["avg_time_ms"]):
        print(f"{r['name']:<25} {r['avg_time_ms']:<10.1f}ms {'—' if r['errors'] == 0 else r['errors']:<8} {r['tasks']:<8}")
    print("─" * 60)

    fastest = min(results, key=lambda r: r["avg_time_ms"])
    print(f"\n🏆 Fastest: {fastest['name']} ({fastest['avg_time_ms']:.1f}ms avg)")

    # Recording for docs
    print("\n✅ Benchmark complete.")
    return results


if __name__ == "__main__":
    run_benchmarks()
