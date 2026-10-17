"""Reproducible simulated UI task; no host desktop or shell access."""
import json
from .core.agent import Agent
from .adapters.mock_adapter import MockAdapter
from .safety.guardrails import Guardrails

class Desktop:
    width, height = 80, 40
    def __init__(self):
        self.windows = []
        self.opened = False
        self.value = ""
    def framebuffer(self):
        return "Name: " + self.value if self.opened else "Open settings"
    def click(self, x, y, button="left"):
        if not self.opened and button == "left" and 0 <= x < 13 and 0 <= y < 10:
            self.opened = True
            return "settings opened"
        raise ValueError("no control at target")
    def type_text(self, text):
        if not self.opened:
            raise ValueError("no focused field")
        self.value += text
        return "field updated"
    def hotkey(self, combo):
        raise ValueError("unsupported simulated shortcut")
    def scroll(self, direction, amount):
        return "no scrollable content"
    def bash(self, command):
        raise ValueError("shell unavailable in demo")

def run_demo():
    env = Desktop()
    agent = Agent(env, MockAdapter([
        {"ground": "Open settings"},
        {"action": "type", "params": {"text": "Peyman"}},
        {"done": True},
    ]), Guardrails(screen_bounds=(80, 40)),
        verifier=lambda env, goal: env.opened and env.value == "Peyman")
    result = agent.run("Open settings and enter Peyman")
    return {"success": result.success, "stop_reason": result.stop_reason,
            "steps": result.n_steps, "latency_ms": result.total_latency_ms,
            "backend": "simulated-text-desktop", "adapter": "scripted",
            "model_inference": False, "api_tokens": 0,
            "final_state": {"settings_open": env.opened, "name": env.value}}

if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
