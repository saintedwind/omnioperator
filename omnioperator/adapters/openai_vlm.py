"""OpenAI GPT-4o / GPT-4V vision adapter for OmniOperator.

The heavy `openai` SDK is imported lazily so the rest of the framework (and
the whole test suite) runs without it installed. In production the adapter
sends the gridded screenshot plus the ReAct history and expects a strict
JSON action proposal back; a defensive parser falls back to a safe "wait"
action on malformed output.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .base import BaseLLMAdapter


class OpenAIVLMAdapter(BaseLLMAdapter):
    """Adapter for OpenAI vision models (gpt-4o, gpt-4-turbo, gpt-4o-mini)."""

    name = "openai_vlm"

    SYSTEM_PROMPT = (
        "You are OmniOperator, an OS automation agent. You see a simulated text framebuffer "
        "of the current screen with a labelled coordinate grid. Respond ONLY "
        "with a JSON object: {\"thought\": str, \"action\": one of "
        "[click, type, hotkey, scroll, bash, done], \"params\": object, "
        "\"done\": bool}. Click coordinates must be integers from the grid."
    )

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None,
                 temperature: float = 0.0, max_tokens: int = 512,
                 client: Any = None) -> None:
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._tokens = 0
        if client is not None:
            self._client = client          # dependency injection for tests
        else:
            try:
                from openai import OpenAI  # lazy import
            except ImportError as exc:      # pragma: no cover
                raise RuntimeError(
                    "The 'openai' package is required for OpenAIVLMAdapter; "
                    "pip install openai") from exc
            self._client = OpenAI(api_key=api_key)

    # ------------------------------------------------------------------
    def propose_action(self, observation: Dict[str, Any],
                       history: List[Dict[str, Any]],
                       goal: str) -> Dict[str, Any]:
        messages = self._build_messages(observation, history, goal)
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = getattr(resp, "usage", None)
        self._tokens += getattr(usage, "total_tokens", 0) or 0
        raw = resp.choices[0].message.content or ""
        return self._parse(raw)

    # ------------------------------------------------------------------
    def _build_messages(self, observation: Dict[str, Any],
                        history: List[Dict[str, Any]],
                        goal: str) -> List[Dict[str, Any]]:
        msgs: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Goal: {goal}"},
        ]
        for step in history:
            msgs.append({"role": "assistant",
                         "content": json.dumps(step, ensure_ascii=False)})
        screenshot = observation.get("screenshot", "")
        ocr_text = "\n".join(observation.get("ocr_text", []))
        msgs.append({"role": "user", "content":
                     f"Simulated text framebuffer (not an image):\n{screenshot}\n\n"
                     f"OCR text:\n{ocr_text}\n\nPropose the next action as JSON."})
        return msgs

    # ------------------------------------------------------------------
    @staticmethod
    def _parse(raw: str) -> Dict[str, Any]:
        """Defensive JSON extraction; never raises on malformed model output."""
        fallback = {"thought": f"unparseable model output: {raw[:200]}",
                    "action": "wait", "params": {}, "done": False,
                    "tokens": 0}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return fallback
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                return fallback
        if (not isinstance(data, dict) or "action" not in data
                or not isinstance(data["action"], str)
                or data["action"] not in {"click", "type", "hotkey", "scroll", "bash", "done"}
                or type(data.get("done", False)) is not bool
                or not isinstance(data.get("params", {}), dict)) :
            return fallback
        return {
            "thought": str(data.get("thought", "")),
            "action": str(data["action"]),
            "params": data.get("params") if isinstance(data.get("params"), dict) else {},
            "done": bool(data.get("done", data.get("action") == "done")),
            "tokens": 0,
        }

    # ------------------------------------------------------------------
    def token_count(self) -> int:
        return self._tokens
