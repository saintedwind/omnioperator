import pytest

from omnioperator.safety.guardrails import Guardrails


def test_destructive_shell_command_is_blocked_and_audited():
    policy = Guardrails()
    result = policy.check("bash", {"command": "rm -rf /"})

    assert result.decision == "BLOCKED"
    assert not result.allowed
    assert "destructive" in result.reason
    assert policy.audit_log[-1]["decision"] == "BLOCKED"


def test_impactful_command_requires_confirmation():
    policy = Guardrails(allow_shell=True)
    pending = policy.check("bash", {"command": "pip install sample-package"})
    confirmed = policy.check(
        "bash", {"command": "pip install sample-package"}, confirmed=True
    )

    assert pending.decision == "CONFIRM"
    assert not pending.allowed
    assert confirmed.decision == "ALLOWED"
    assert confirmed.allowed


def test_shell_disabled_instead_of_claiming_regex_sandbox():
    policy = Guardrails(workspace_root="/workspace")
    result = policy.check("bash", {"command": "cat /private/data.txt"})

    assert result.decision == "BLOCKED"
    assert not result.allowed


def test_destructive_click_and_out_of_bounds_click_are_blocked():
    policy = Guardrails(screen_bounds=(100, 80))

    destructive = policy.check("click", {"x": 10, "y": 10, "label": "Delete all files"})
    outside = policy.check("click", {"x": 100, "y": 10})

    assert destructive.decision == "BLOCKED"
    assert outside.decision == "BLOCKED"


def test_type_length_and_scroll_amount_are_sanitized():
    policy = Guardrails(max_type_chars=4)
    typed = policy.check("type", {"text": "abcdef"})
    scroll = policy.check("scroll", {"direction": "down", "amount": 100})

    assert typed.decision == "SANITIZE"
    assert typed.params == {"text": "abcd"}
    assert scroll.decision == "ALLOWED"
    assert scroll.params["amount"] == 30


@pytest.mark.parametrize("combo", ["ctrl+alt+del", "alt+f4", "super+l"])
def test_session_terminating_hotkeys_are_blocked(combo):
    result = Guardrails().check("hotkey", {"combo": combo})
    assert result.decision == "BLOCKED"
    assert not result.allowed
