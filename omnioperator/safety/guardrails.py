"""Validation policy for simulated actions; not an operating-system sandbox."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern


@dataclass
class GuardrailDecision:
    """Outcome of a guardrail evaluation."""
    decision: str            # ALLOWED | CONFIRM | SANITIZE | BLOCKED
    reason: str
    allowed: bool
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.params:
            self.params = dict(self.params)


class Guardrails:
    """Configurable action-safety policy."""

    DECISIONS = ("ALLOWED", "CONFIRM", "SANITIZE", "BLOCKED")

    #: shell patterns that are always rejected outright
    DESTRUCTIVE_PATTERNS: List[Pattern[str]] = [
        re.compile(p, re.IGNORECASE) for p in (
            r"\brm\s+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)\b",
            r"\brm\s+-[a-z]*r[a-z]*\b.*\s+/(?:\s|$)",
            r"\bmkfs\b", r"\bdd\b\s+.*\bof=/dev/", r"\bshutdown\b",
            r"\breboot\b", r"\bhalt\b", r":\(\)\s*\{.*\};\s*:",
            r"\bchmod\s+(-R\s+)?777\s+/", r"\bkill(all)?\s+-9\s+1\b",
            r"\bmv\b.*\s+/(?:\s|$)", r"\b>\s*/dev/sd[a-z]",
        )
    ]

    #: shell patterns that are allowed only with explicit human confirmation
    CONFIRM_PATTERNS: List[Pattern[str]] = [
        re.compile(p, re.IGNORECASE) for p in (
            r"\bapt(-get)?\s+(install|remove|purge)\b",
            r"\bpip3?\s+(install|uninstall)\b",
            r"\bcurl\b", r"\bwget\b", r"\bsudo\b", r"\btar\b.*\bxzf\b",
            r"\bkill\b", r"\bcrontab\b", r"\bgit\s+push\b",
        )
    ]

    #: destructive verbs we refuse to click on (button labels)
    DESTRUCTIVE_CLICK_LABELS = ("delete all", "format", "erase disk",
                                "wipe", "factory reset")

    def __init__(self,
                 workspace_root: str = "/workspace",
                 require_confirmation_for: Optional[set] = None,
                 max_type_chars: int = 10_000,
                 screen_bounds: Optional[tuple] = None,
                 allow_shell: bool = False) -> None:
        if type(max_type_chars) is not int or max_type_chars < 1:
            raise ValueError("max_type_chars must be a positive integer")
        if screen_bounds is not None and (len(screen_bounds) != 2 or any(type(v) is not int or v <= 0 for v in screen_bounds)):
            raise ValueError("screen bounds must be positive integers")
        self.allow_shell = allow_shell
        self.workspace_root = workspace_root.rstrip("/")
        self.require_confirmation_for = set(require_confirmation_for or set())
        self.max_type_chars = max_type_chars
        self.screen_bounds = screen_bounds  # (width, height) or None
        self.audit_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def check(self, action: str, params: Dict[str, Any],
              confirmed: bool = False) -> GuardrailDecision:
        """Evaluate one proposed action and return the decision."""
        if not isinstance(params, dict):
            return GuardrailDecision("BLOCKED", "params must be an object", False)
        decision = self._evaluate(action, params, confirmed)
        if decision.allowed and action in self.require_confirmation_for and not confirmed:
            decision = GuardrailDecision("CONFIRM", "action requires operator approval", False)
        self.audit_log.append({
            "action": action,
            "params": dict(params),
            "confirmed": confirmed,
            "decision": decision.decision,
            "reason": decision.reason,
        })
        return decision

    # ------------------------------------------------------------------
    def _evaluate(self, action: str, params: Dict[str, Any],
                  confirmed: bool) -> GuardrailDecision:
        if action == "bash":
            return self._check_bash(params.get("command", ""), confirmed)

        if action == "click":
            return self._check_click(params)

        if action == "type":
            return self._check_type(params)

        if action == "hotkey":
            return self._check_hotkey(params.get("combo", ""))

        if action == "scroll":
            return self._check_scroll(params)

        return GuardrailDecision("BLOCKED", f"unknown action '{action}'", False)

    # -- bash -----------------------------------------------------------
    def _check_bash(self, command: str, confirmed: bool) -> GuardrailDecision:
        if not isinstance(command, str):
            return GuardrailDecision("BLOCKED", "command must be a string", False)
        cmd = command.strip()
        if not cmd:
            return GuardrailDecision("BLOCKED", "empty shell command", False)

        for pat in self.DESTRUCTIVE_PATTERNS:
            if pat.search(cmd):
                return GuardrailDecision("BLOCKED",
                                         f"destructive shell pattern matched: {pat.pattern}",
                                         False)

        # A command string cannot be made into an OS sandbox by regex rewriting.
        if not self.allow_shell:
            return GuardrailDecision("BLOCKED", "shell capability disabled", False)
        if not confirmed:
            return GuardrailDecision("CONFIRM", "each shell action requires operator approval", False)
        return GuardrailDecision("ALLOWED", "approved shell; backend isolation required", True,
                                 {"command": cmd})

    # -- click ----------------------------------------------------------
    def _check_click(self, params: Dict[str, Any]) -> GuardrailDecision:
        try:
            x, y = params["x"], params["y"]
            if type(x) is not int or type(y) is not int or x < 0 or y < 0:
                raise ValueError("invalid coordinates")
        except (KeyError, TypeError, ValueError):
            return GuardrailDecision("BLOCKED", "click requires integer x and y", False)
        if self.screen_bounds:
            w, h = self.screen_bounds
            if not (0 <= x < w and 0 <= y < h):
                return GuardrailDecision(
                    "BLOCKED", f"click ({x},{y}) outside screen bounds {self.screen_bounds}",
                    False)
        if params.get("button", "left") not in ("left", "right", "middle"):
            return GuardrailDecision("BLOCKED", "invalid mouse button", False)
        label = str(params.get("label", "")).lower()
        for bad in self.DESTRUCTIVE_CLICK_LABELS:
            if bad in label:
                return GuardrailDecision(
                    "BLOCKED", f"refusing to click destructive control '{label}'", False)
        return GuardrailDecision("ALLOWED", "safe click", True,
                                 {"x": x, "y": y,
                                  **({"button": params["button"]}
                                     if "button" in params else {})})

    # -- type -----------------------------------------------------------
    def _check_type(self, params: Dict[str, Any]) -> GuardrailDecision:
        text = params.get("text", "")
        if not isinstance(text, str):
            return GuardrailDecision("BLOCKED", "text must be a string", False)
        if len(text) > self.max_type_chars:
            return GuardrailDecision(
                "SANITIZE", f"text truncated to {self.max_type_chars} chars", True,
                {"text": text[: self.max_type_chars]})
        return GuardrailDecision("ALLOWED", "safe typing", True, {"text": text})

    # -- hotkey ---------------------------------------------------------
    _BLOCKED_COMBOS = {"ctrl+alt+del", "alt+f4", "ctrl+alt+backspace",
                       "super+l", "meta+l"}

    def _check_hotkey(self, combo: str) -> GuardrailDecision:
        if not isinstance(combo, str):
            return GuardrailDecision("BLOCKED", "combo must be a string", False)
        c = (combo or "").strip().lower().replace(" ", "")
        if not c:
            return GuardrailDecision("BLOCKED", "empty hotkey combo", False)
        if c in self._BLOCKED_COMBOS:
            return GuardrailDecision("BLOCKED",
                                     f"hotkey '{combo}' can terminate or lock the session",
                                     False)
        return GuardrailDecision("ALLOWED", "safe hotkey", True, {"combo": combo})

    # -- scroll ---------------------------------------------------------
    def _check_scroll(self, params: Dict[str, Any]) -> GuardrailDecision:
        direction = str(params.get("direction", "down"))
        if direction not in ("up", "down", "left", "right"):
            return GuardrailDecision("BLOCKED",
                                     f"invalid scroll direction '{direction}'", False)
        try:
            amount = params.get("amount", 3)
            if type(amount) is not int:
                raise ValueError("invalid amount")
        except (TypeError, ValueError):
            return GuardrailDecision("BLOCKED", "scroll amount must be an integer", False)
        amount = max(1, min(amount, 30))
        return GuardrailDecision("ALLOWED", "safe scroll", True,
                                 {"direction": direction, "amount": amount})
