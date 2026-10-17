import pytest
from omnioperator.core.controller import Controller
from omnioperator.core.agent import Agent
from omnioperator.safety.guardrails import Guardrails
from omnioperator.adapters.mock_adapter import MockAdapter
from omnioperator.adapters.openai_vlm import OpenAIVLMAdapter
from omnioperator.demo import Desktop, run_demo

def test_demo_checks_actual_final_state():
    assert run_demo()["success"]

def test_model_done_is_not_success_without_verifier():
    result = Agent(Desktop(), MockAdapter([{"done": True}])).run("anything")
    assert not result.success
    assert result.stop_reason == "unverified_done"

def test_sanitized_parameters_reach_backend():
    env = Desktop(); env.opened = True
    c = Controller(env, Guardrails(max_type_chars=4))
    result = c.execute("type", {"text": "abcdef"})
    assert env.value == "abcd"
    assert result.params == {"text": "abcd"}
    assert result.guardrail == "SANITIZE"

def test_metadata_is_not_passed_to_click_handler():
    result = Controller(Desktop()).execute("click", {"x": 6, "y": 5, "label": "settings"})
    assert result.success

@pytest.mark.parametrize("x", [True, 1.5, "6", -1, float("inf")])
def test_bad_coordinates_never_execute(x):
    assert Controller(Desktop()).execute("click", {"x": x, "y": 5}).blocked

def test_failure_cannot_turn_into_later_success():
    result = Agent(Desktop(), MockAdapter([
        {"action": "type", "params": {"text": "x"}}, {"done": True}
    ]), verifier=lambda e,g: True).run("test")
    assert not result.success
    assert result.stop_reason == "execution_error"

def test_global_confirmation_rejected():
    with pytest.raises(ValueError):
        Agent(Desktop(), MockAdapter([])).run("test", confirmed=True)

@pytest.mark.parametrize("command", ["python -c 'anything'", "cat /workspace/../secret", "echo x > /etc/a", "powershell Remove-Item x"])
def test_shell_is_closed_by_default(command):
    assert not Guardrails().check("bash", {"command": command}, True).allowed

def test_controller_confirmation_setting_enforced():
    c = Controller(Desktop(), require_confirmation_for={"click"})
    assert c.execute("click", {"x":6,"y":5}).guardrail == "CONFIRM"

def test_string_false_is_not_boolean_true():
    assert OpenAIVLMAdapter._parse('{"action":"done","done":"false"}')["action"] == "wait"

@pytest.mark.parametrize("command", [123, [], {}])
def test_invalid_command_types_are_rejected(command):
    assert Guardrails().check("bash", {"command":command}).decision == "BLOCKED"

def test_empty_grounding_has_no_target():
    from omnioperator.core.vision import Vision
    assert Vision(Desktop()).ground_element("") is None
