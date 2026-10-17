"""The OmniOperator ReAct agent.

Ties together three components:

    Vision      – screen perception (grab, grid overlay, grounding, OCR)
    Adapter     – an LLM that proposes the next action
    Controller  – guardrailed executor against the OS environment

The agent runs an observe -> reason -> act loop until the adapter signals
`done`, the step budget is exhausted, or a guardrail aborts the episode.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..adapters.base import BaseLLMAdapter
from ..safety.guardrails import Guardrails
from .controller import ActionResult, Controller
from .vision import Vision


@dataclass
class StepRecord:
    """One iteration of the ReAct loop."""
    step: int
    thought: str
    action: str
    params: Dict[str, Any]
    result: Optional[ActionResult]
    latency_ms: float
    done: bool


@dataclass
class EpisodeResult:
    """Final outcome of one agent episode."""
    goal: str
    success: bool
    steps: List[StepRecord] = field(default_factory=list)
    total_latency_ms: float = 0.0
    tokens_used: int = 0
    stop_reason: str = "done"

    @property
    def n_steps(self) -> int:
        return len(self.steps)

    def summary(self) -> str:
        lines = [f"Episode '{self.goal}': success={self.success} "
                 f"steps={self.n_steps} stop={self.stop_reason} "
                 f"latency={self.total_latency_ms:.1f}ms tokens={self.tokens_used}"]
        for s in self.steps:
            lines.append(f"  {s.step}. think={s.thought[:60]!r} "
                         f"act={s.action}({s.params}) -> "
                         f"{s.result.detail if s.result else 'n/a'}")
        return "\n".join(lines)


class Agent:
    """ReAct-style OS automation agent."""

    def __init__(self, env: Any, adapter: BaseLLMAdapter,
                 guardrails: Optional[Guardrails] = None,
                 max_steps: int = 15,
                 step_budget_seconds: float = 120.0,
                 verifier: Any = None) -> None:
        if type(max_steps) is not int or max_steps < 1 or step_budget_seconds <= 0:
            raise ValueError("budgets must be positive")
        self.verifier = verifier
        self.env = env
        self.adapter = adapter
        self.vision = Vision(env)
        self.controller = Controller(env, guardrails=guardrails)
        self.max_steps = max_steps
        self.step_budget_seconds = step_budget_seconds

    # ------------------------------------------------------------------
    def run(self, goal: str, confirmed: bool = False) -> EpisodeResult:
        """Run one full episode for `goal` and return a structured result."""
        if confirmed:
            raise ValueError("episode-wide confirmation is unsafe; use controller per action")
        episode = EpisodeResult(goal=goal, success=False)
        self.controller.reset_trace()
        initial_tokens = self.adapter.token_count()
        history: List[Dict[str, Any]] = []
        t_start = time.perf_counter()

        for step_no in range(1, self.max_steps + 1):
            if time.perf_counter() - t_start > self.step_budget_seconds:
                episode.stop_reason = "time_budget"
                break

            observation = self.vision.observe()
            t0 = time.perf_counter()
            try:
                proposal = self.adapter.propose_action(observation, history, goal)
                if not isinstance(proposal, dict) or not isinstance(proposal.get("params", {}), dict):
                    raise ValueError("malformed proposal")
                if type(proposal.get("done", False)) is not bool:
                    raise ValueError("done must be boolean")
            except Exception:
                episode.stop_reason = "adapter_error"
                break
            if time.perf_counter() - t_start > self.step_budget_seconds:
                episode.stop_reason = "time_budget"
                break
            thought = str(proposal.get("thought", ""))
            action = str(proposal.get("action", "wait"))
            params = dict(proposal.get("params") or {})
            lat = (time.perf_counter() - t0) * 1000.0

            if proposal.get("done") or action == "done":
                episode.steps.append(StepRecord(
                    step_no, thought, "done", {}, None, lat, True))
                try:
                    episode.success = bool(self.verifier(self.env, goal)) if self.verifier else False
                    episode.stop_reason = "done" if episode.success else "unverified_done"
                except Exception:
                    episode.stop_reason = "verification_error"
                break

            # No episode-wide approval; policy handles each proposed action.
            need_confirm = confirmed
            result = self.controller.execute(action, params, confirmed=need_confirm)

            episode.steps.append(StepRecord(
                step_no, thought, action, params, result,
                lat + result.latency_ms, False))
            history.append({
                "step": step_no, "thought": thought, "action": action,
                "params": params, "result": result.detail,
                "success": result.success, "blocked": result.blocked,
            })

            if not result.success and not result.blocked:
                episode.stop_reason = "execution_error"
                break
            if result.blocked:
                episode.stop_reason = f"guardrail:{result.guardrail}"
                break
        else:
            episode.stop_reason = "max_steps"

        episode.total_latency_ms = (time.perf_counter() - t_start) * 1000.0
        episode.tokens_used = max(0, self.adapter.token_count() - initial_tokens)
        return episode
