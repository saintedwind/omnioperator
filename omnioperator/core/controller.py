"""Action executor for OmniOperator.

Executes a discrete set of primitive OS-level actions against a `SimulatedOS`
backed environment (or, in production, a real OS backend). Every action goes
through a security guardrail check before execution.

Supported actions:
    - click(x, y)
    - type(text)
    - hotkey(combo)
    - scroll(direction, amount)
    - bash(command)   # only via guardrailed fallback

All latencies are measured in real wall-clock time (time.perf_counter()).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..safety.guardrails import Guardrails, GuardrailDecision


@dataclass
class ActionResult:
    """Structured result of a single executed action."""
    action: str
    params: Dict[str, Any]
    success: bool
    detail: str
    latency_ms: float
    guardrail: str = "ALLOWED"
    blocked: bool = False


@dataclass
class ExecutionTrace:
    """Ordered log of every action the controller actually executed."""
    entries: List[ActionResult] = field(default_factory=list)

    def add(self, r: ActionResult) -> None:
        self.entries.append(r)

    @property
    def total_actions(self) -> int:
        return len(self.entries)

    @property
    def blocked_actions(self) -> int:
        return sum(1 for e in self.entries if e.blocked)

    @property
    def total_latency_ms(self) -> float:
        return sum(e.latency_ms for e in self.entries)

    def summary(self) -> str:
        lines = [f"  {i+1}. [{e.action}] guardrail={e.guardrail} "
                 f"ok={e.success} blocked={e.blocked} latency={e.latency_ms:.3f}ms :: {e.detail}"
                 for i, e in enumerate(self.entries)]
        return "\n".join(lines)


class Controller:
    """Executes grounded actions on a target OS-like environment.

    The controller NEVER decides *what* to do — it only executes actions
    requested by the agent, after consulting the Guardrails policy layer.
    """

    #: primitive actions exposed to the agent
    ACTIONS = ("click", "type", "hotkey", "scroll", "bash")

    def __init__(self, env: Any, guardrails: Optional[Guardrails] = None,
                 require_confirmation_for: Optional[set] = None) -> None:
        self.env = env
        self.guardrails = guardrails or Guardrails()
        self.require_confirmation_for = ({"bash"} if require_confirmation_for is None else set(require_confirmation_for))
        self.trace = ExecutionTrace()

    # ------------------------------------------------------------------
    def execute(self, action: str, params: Dict[str, Any],
                confirmed: bool = False) -> ActionResult:
        """Execute one action after a guardrail check."""
        if action not in self.ACTIONS:
            res = ActionResult(action, params, False,
                               f"unknown action '{action}'", 0.0,
                               guardrail="INVALID", blocked=True)
            self.trace.add(res)
            return res

        t0 = time.perf_counter()
        decision: GuardrailDecision = self.guardrails.check(action, params, confirmed)
        if decision.allowed and action in self.require_confirmation_for and not confirmed:
            decision = GuardrailDecision("CONFIRM", "controller requires action confirmation", False)
        t1 = time.perf_counter()

        if not decision.allowed:
            res = ActionResult(action, params, False,
                               decision.reason, (t1 - t0) * 1000.0,
                               guardrail=decision.decision, blocked=True)
            self.trace.add(res)
            return res

        handler: Callable[..., Any] = getattr(self, f"_do_{action}")
        try:
            detail = handler(**decision.params)
            ok, detail = True, detail
        except Exception as exc:  # noqa: BLE001 — guardrail of last resort
            ok, detail = False, f"execution error: {exc}"
        t2 = time.perf_counter()

        res = ActionResult(action, dict(decision.params), ok, detail,
                           (t2 - t0) * 1000.0, guardrail=decision.decision)
        self.trace.add(res)
        return res

    # ------------------------------------------------------------------
    # Primitive handlers — each talks to the SimulatedOS environment.
    def _do_click(self, x: int, y: int, button: str = "left") -> str:
        return self.env.click(x, y, button=button)

    def _do_type(self, text: str) -> str:
        return self.env.type_text(text)

    def _do_hotkey(self, combo: str) -> str:
        return self.env.hotkey(combo)

    def _do_scroll(self, direction: str, amount: int = 3) -> str:
        return self.env.scroll(direction, amount)

    def _do_bash(self, command: str) -> str:
        return self.env.bash(command)

    # Convenience for tests / reports
    def reset_trace(self) -> None:
        self.trace = ExecutionTrace()
