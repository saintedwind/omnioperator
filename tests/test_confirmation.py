from unittest.mock import Mock

import pytest

from omnioperator.core.controller import Controller
from omnioperator.safety.guardrails import Guardrails


@pytest.mark.parametrize("confirmed", ["false", "true", 1, 0, None, [], {"approved": True}])
@pytest.mark.parametrize("scope", ["shell", "policy", "controller"])
def test_non_boolean_confirmation_never_executes(confirmed, scope):
    env = Mock()
    policy = Guardrails(allow_shell=True,
                        require_confirmation_for={"type"} if scope == "policy" else set())
    controller = Controller(env, policy, require_confirmation_for={"type"})
    action, params = ("bash", {"command": "echo ok"}) if scope == "shell" else ("type", {"text": "ok"})
    result = controller.execute(action, params, confirmed=confirmed)
    assert result.blocked
    assert not result.success
    assert env.mock_calls == []
    assert policy.audit_log[-1]["decision"] == "BLOCKED"


@pytest.mark.parametrize("confirmed", [False, True])
@pytest.mark.parametrize("action,params", [("bash", {"command": "echo ok"}), ("type", {"text": "ok"})])
def test_boolean_confirmation_preserves_approval_flow(confirmed, action, params):
    env = Mock()
    controller = Controller(env, Guardrails(allow_shell=True),
                            require_confirmation_for={"type", "bash"})
    result = controller.execute(action, params, confirmed=confirmed)
    assert result.success is confirmed
    assert result.blocked is not confirmed
    assert len(env.mock_calls) == int(confirmed)
