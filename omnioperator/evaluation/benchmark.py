"""Reproducible benchmark harness for OmniOperator.

Runs the agent over a suite of scripted tasks on the simulated OS and
computes success rate, mean steps, mean latency and token cost. Produces a
structured `BenchmarkReport` that can be exported to JSON or Markdown.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Task:
    """One benchmark task: a goal plus the environment setup + oracle."""
    task_id: str
    goal: str
    setup: Callable[[Any], Any]                 # mutates the env before the run
    oracle: Callable[[Any, "EpisodeLike"], bool]  # success predicate
    category: str = "general"


@dataclass
class TaskResult:
    task_id: str
    category: str
    goal: str
    success: bool
    n_steps: int
    total_latency_ms: float
    tokens_used: int
    stop_reason: str
    error: Optional[str] = None


@dataclass
class BenchmarkReport:
    model: str
    results: List[TaskResult] = field(default_factory=list)

    @property
    def n_tasks(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        return (sum(r.success for r in self.results) / self.n_tasks) if self.n_tasks else 0.0

    @property
    def mean_steps(self) -> float:
        return (sum(r.n_steps for r in self.results) / self.n_tasks) if self.n_tasks else 0.0

    @property
    def mean_latency_ms(self) -> float:
        return (sum(r.total_latency_ms for r in self.results) / self.n_tasks) if self.n_tasks else 0.0

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens_used for r in self.results)

    def by_category(self) -> Dict[str, float]:
        cats: Dict[str, List[bool]] = {}
        for r in self.results:
            cats.setdefault(r.category, []).append(r.success)
        return {c: sum(v) / len(v) for c, v in sorted(cats.items())}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps({
            "model": self.model,
            "success_rate": round(self.success_rate, 4),
            "mean_steps": round(self.mean_steps, 2),
            "mean_latency_ms": round(self.mean_latency_ms, 2),
            "total_tokens": self.total_tokens,
            "by_category": self.by_category(),
            "results": [asdict(r) for r in self.results],
        }, indent=indent)

    def to_markdown(self) -> str:
        lines = [
            f"# OmniOperator Benchmark — {self.model}",
            "",
            f"- Tasks: **{self.n_tasks}**",
            f"- Success rate: **{self.success_rate:.1%}**",
            f"- Mean steps: **{self.mean_steps:.2f}**",
            f"- Mean latency: **{self.mean_latency_ms:.1f} ms**",
            f"- Total tokens: **{self.total_tokens}**",
            "",
            "| task | category | success | steps | latency (ms) | tokens | stop |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in self.results:
            lines.append(
                f"| {r.task_id} | {r.category} | {'✅' if r.success else '❌'} "
                f"| {r.n_steps} | {r.total_latency_ms:.1f} | {r.tokens_used} "
                f"| {r.stop_reason} |")
        return "\n".join(lines)


class Benchmark:
    """Runs a list of Tasks against an agent factory (fresh agent per task)."""

    def __init__(self, tasks: List[Task],
                 agent_factory: Callable[[], Any],
                 model_name: str = "unknown") -> None:
        self.tasks = tasks
        self.agent_factory = agent_factory
        self.model_name = model_name

    # ------------------------------------------------------------------
    def run(self, goal_flag: str = "") -> BenchmarkReport:
        if goal_flag:
            raise ValueError("benchmark cannot grant blanket action approval")
        report = BenchmarkReport(model=self.model_name)
        for task in self.tasks:
            try:
                agent = self.agent_factory()
                env = agent.env
                task.setup(env)
                t0 = time.perf_counter()
                episode = agent.run(task.goal, confirmed=bool(goal_flag))
                wall = (time.perf_counter() - t0) * 1000.0
                ok = bool(task.oracle(env, episode))
                report.results.append(TaskResult(
                    task_id=task.task_id, category=task.category,
                    goal=task.goal, success=ok, n_steps=episode.n_steps,
                    total_latency_ms=wall, tokens_used=episode.tokens_used,
                    stop_reason=episode.stop_reason))
            except Exception as exc:  # noqa: BLE001 — benchmark must not die
                report.results.append(TaskResult(
                    task_id=task.task_id, category=task.category,
                    goal=task.goal, success=False, n_steps=0,
                    total_latency_ms=0.0, tokens_used=0,
                    stop_reason="error", error=str(exc)))
        return report
