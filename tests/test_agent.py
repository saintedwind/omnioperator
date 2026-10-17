from omnioperator.adapters.mock_adapter import MockAdapter
from omnioperator.core.agent import Agent
from omnioperator.safety.guardrails import Guardrails


class TinyDesktop:
    """Small deterministic environment implementing the controller/vision API."""

    width = 80
    height = 40
    windows = []

    def __init__(self):
        self.actions = []

    def framebuffer(self):
        return "Open settings\n" + " " * 70 + "\n" + " " * 80

    def click(self, x, y, button="left"):
        self.actions.append(("click", x, y, button))
        return f"clicked at ({x}, {y})"

    def type_text(self, text):
        self.actions.append(("type", text))
        return f"typed {len(text)} characters"

    def hotkey(self, combo):
        self.actions.append(("hotkey", combo))
        return f"pressed {combo}"

    def scroll(self, direction, amount):
        self.actions.append(("scroll", direction, amount))
        return f"scrolled {direction} by {amount}"

    def bash(self, command):
        self.actions.append(("bash", command))
        return "command executed"


def test_agent_grounds_click_types_then_finishes():
    env = TinyDesktop()
    adapter = MockAdapter([
        {"ground": "Open settings"},
        {"action": "type", "params": {"text": "hello"}},
        {"done": True},
    ])
    agent = Agent(env, adapter, guardrails=Guardrails(screen_bounds=(80, 40)),
                  verifier=lambda env, goal: ("type", "hello") in env.actions)

    episode = agent.run("open settings and enter hello")

    assert episode.success
    assert episode.stop_reason == "done"
    assert episode.n_steps == 3
    assert [action[0] for action in env.actions] == ["click", "type"]
    assert env.actions[0][1:3] == (6, 5)
    assert env.actions[1] == ("type", "hello")
    assert agent.controller.trace.total_actions == 2


def test_agent_stops_when_guardrail_blocks_proposed_action():
    env = TinyDesktop()
    adapter = MockAdapter([
        {"action": "bash", "params": {"command": "rm -rf /"}},
    ])
    agent = Agent(env, adapter)

    episode = agent.run("clean up")

    assert not episode.success
    assert episode.n_steps == 1
    assert episode.stop_reason.startswith("guardrail:BLOCKED")
    assert env.actions == []
    assert agent.controller.trace.blocked_actions == 1
