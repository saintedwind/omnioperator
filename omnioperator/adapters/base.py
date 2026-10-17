"""Abstract base class for every OmniOperator LLM adapter."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMAdapter(ABC):
    """Minimal contract: the agent sends an Observation + history and the
    adapter returns a structured action proposal."""

    name: str = "base"

    @abstractmethod
    def propose_action(self, observation: Dict[str, Any],
                       history: List[Dict[str, Any]],
                       goal: str) -> Dict[str, Any]:
        """Return {"thought": str, "action": str, "params": dict,
                   "done": bool, "tokens": int}."""

    @abstractmethod
    def token_count(self) -> int:
        """Cumulative tokens consumed by this adapter instance."""
