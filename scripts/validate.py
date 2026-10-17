"""Local acceptance run: independent state checks, no network or API calls."""
import json
import platform
from pathlib import Path
from datetime import datetime, timezone
from omnioperator.demo import Desktop, run_demo
from omnioperator.core.agent import Agent
from omnioperator.adapters.mock_adapter import MockAdapter
from omnioperator.core.controller import Controller
from omnioperator.safety.guardrails import Guardrails

results = []
demo = run_demo()
results.append({"case":"complete_task", "passed":demo["success"], "evidence":demo})
env = Desktop()
r = Agent(env, MockAdapter([{"done":True}]), verifier=lambda e,g:e.value == "Peyman").run("enter name")
results.append({"case":"false_completion", "passed":not r.success, "stop":r.stop_reason})
env = Desktop(); env.opened = True
r = Controller(env, Guardrails(max_type_chars=4)).execute("type", {"text":"abcdef"})
results.append({"case":"sanitization_reaches_backend", "passed":env.value == "abcd", "stored":env.value})
env = Desktop()
r = Controller(env).execute("bash", {"command":"echo hello"}, confirmed=True)
results.append({"case":"shell_disabled", "passed":r.blocked, "decision":r.guardrail})
report = {"checked_at":datetime.now(timezone.utc).isoformat(), "python":platform.python_version(),
          "kind":"local simulated integration; not real desktop or model inference",
          "results":results, "passed":all(r["passed"] for r in results)}
Path("reports").mkdir(exist_ok=True)
Path("reports/acceptance.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
raise SystemExit(0 if report["passed"] else 1)
