"""Deterministic, vision-aware mock adapter used for reproducible tests.

The mock adapter inspects the *actual* framebuffer observation (so it is
text-grounded in a simulation) and emits the next primitive action according to
the task script supplied by the test — scripted test data; no model inference.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .base import BaseLLMAdapter


class MockAdapter(BaseLLMAdapter):
    name = "mock"

    def __init__(self, plan: List[Dict[str, Any]]) -> None:
        """`plan` is a list of steps:
            {"ground": "<element query>"}            -> vision-ground then click
            {"action": "type", "params": {...}}      -> emit typed action
            {"action": "bash", "params": {...}}      -> emit bash action
            {"action": "hotkey", "params": {...}}    -> emit hotkey action
            {"done": True}                            -> finish
        """
        self._plan = list(plan)
        self._cursor = 0
        self._tokens = 0

    # ------------------------------------------------------------------
    def propose_action(self, observation: Dict[str, Any],
                       history: List[Dict[str, Any]],
                       goal: str) -> Dict[str, Any]:
        if self._cursor >= len(self._plan):
            return {"thought": "plan exhausted", "action": "done",
                    "params": {}, "done": True, "tokens": 0}

        step = self._plan[self._cursor]
        self._cursor += 1

        # Vision-grounded click step
        if "ground" in step:
            fb = observation.get("raw_framebuffer", "")
            query = step["ground"]
            found = self._find(fb, query)
            self._tokens += len(observation.get("screenshot", "")) // 4
            if found is None:
                return {"thought": f"'{query}' not visible on screen",
                        "action": "wait", "params": {}, "done": False,
                        "tokens": self._tokens}
            x, y = found
            return {"thought": f"grounded '{query}' at ({x},{y}) in framebuffer",
                    "action": "click", "params": {"x": x, "y": y},
                    "done": False, "tokens": self._tokens}

        if step.get("done"):
            self._tokens += len(str(step)) // 4
            return {"thought": step.get("thought", "finished"),
                    "action": "done", "params": {}, "done": True,
                    "tokens": self._tokens}

        self._tokens += len(str(step)) // 4
        return {"thought": step.get("thought", "scripted step"),
                "action": step["action"], "params": step.get("params", {}),
                "done": False, "tokens": self._tokens}

    # ------------------------------------------------------------------
    def token_count(self) -> int:
        return self._tokens

    @staticmethod
    def _find(fb: str, query: str):
        for r, line in enumerate(fb.rstrip("\n").split("\n")):
            c = line.find(query)
            if c >= 0:
                return (c + max(0, len(query) // 2), r * 10 + 5)
        return None
