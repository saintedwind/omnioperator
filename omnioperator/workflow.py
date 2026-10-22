"""Real file-processing backend; explicitly not desktop/vision automation."""
import csv
import hashlib
import io
import json
import math
import statistics
from pathlib import Path

FIELDS = ("CO(GT)", "PT08.S1(CO)", "NMHC(GT)", "C6H6(GT)", "PT08.S2(NMHC)",
          "NOx(GT)", "PT08.S3(NOx)", "NO2(GT)", "PT08.S4(NO2)", "PT08.S5(O3)", "T", "RH", "AH")

def analyze(raw):
    if len(raw) > 2_000_000:
        raise ValueError("dataset exceeds 2 MB limit")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";")
    if not {"Date", "Time", *FIELDS}.issubset(reader.fieldnames or []):
        raise ValueError("unexpected dataset schema")
    columns = {name: [] for name in FIELDS}
    missing = {name: 0 for name in FIELDS}
    rows = blank = 0
    dates = []
    for row in reader:
        if not any((value or "").strip() for key,value in row.items() if key):
            blank += 1
            continue
        if not row.get("Date") or not row.get("Time"):
            raise ValueError("incomplete timestamp")
        from datetime import datetime
        dates.append(datetime.strptime(row["Date"] + " " + row["Time"], "%d/%m/%Y %H.%M.%S"))
        rows += 1
        for name in FIELDS:
            cell = (row[name] or "").strip()
            value = float(cell.replace(",", ".")) if cell else None
            if value is not None and not math.isfinite(value):
                raise ValueError("nonfinite sensor value")
            if value is None or value == -200:
                missing[name] += 1
            else:
                columns[name].append(value)
    if not rows:
        raise ValueError("dataset is empty")
    return {"source_sha256": hashlib.sha256(raw).hexdigest(), "rows": rows,
            "blank_rows_skipped": blank, "start":min(dates).isoformat(), "end":max(dates).isoformat(),
            "duplicate_timestamps":len(dates)-len(set(dates)),
            "columns":{name:{"valid":len(values), "missing":missing[name],
            "missing_percent":round(100*missing[name]/rows,4),
            "mean":round(statistics.fmean(values),6) if values else None}
            for name,values in columns.items()}}

class DatasetWorkspace:
    """Capability backend: fixed source, fixed report destination, no shell."""
    width, height = 100, 50
    def __init__(self, source, output, expected_sha256):
        self.source = Path(source)
        self.output = Path(output)
        self.expected_sha256 = expected_sha256
        self.windows = []
        self.pending = ""
        self.status = "Ready: inspect then export"
        self.report = None
    def framebuffer(self):
        return json.dumps({"status":self.status,"selected":self.pending,"inspected":self.report is not None,"exported":self.status == "Export complete"})
    def type_text(self, text):
        if text not in {"inspect", "export"}:
            raise ValueError("only inspect/export capabilities exist")
        self.pending = text
        return "operation selected"
    def hotkey(self, combo):
        if combo != "ctrl+enter":
            raise ValueError("unsupported shortcut")
        if self.pending == "inspect":
            raw = self.source.read_bytes()
            if hashlib.sha256(raw).hexdigest() != self.expected_sha256:
                raise ValueError("source checksum mismatch")
            self.report = analyze(raw)
            self.status = "Inspected %s records" % self.report["rows"]
        elif self.pending == "export" and self.report is not None:
            self.output.parent.mkdir(parents=True,exist_ok=True)
            self.output.write_text(json.dumps(self.report,indent=2),encoding="utf-8")
            self.status = "Export complete"
        else:
            raise ValueError("inspect before export")
        self.pending = ""
        return self.status
    def click(self, *args, **kwargs):
        raise ValueError("this backend exposes no GUI")
    def scroll(self, *args, **kwargs):
        raise ValueError("this backend exposes no GUI")
    def bash(self, command):
        raise ValueError("shell unavailable")

def run_workflow(source, output, expected_sha256):
    from .core.agent import Agent
    from .adapters.mock_adapter import MockAdapter
    env = DatasetWorkspace(source,output,expected_sha256)
    plan = [{"action":"type","params":{"text":operation}} if kind == "select" else
            {"action":"hotkey","params":{"combo":"ctrl+enter"}}
            for operation in ("inspect","export") for kind in ("select","execute")]
    plan.append({"done":True})
    def verify(env, goal):
        if not env.output.is_file():
            return False
        stored = json.loads(env.output.read_text(encoding="utf-8"))
        return env.status == "Export complete" and stored == analyze(env.source.read_bytes())
    episode = Agent(env,MockAdapter(plan),verifier=verify).run("Inspect source sensor data and export a quality report")
    return {"success":episode.success,"stop_reason":episode.stop_reason,"steps":episode.n_steps,
            "latency_ms":episode.total_latency_ms,"backend":"real-file-workflow",
            "planner":"scripted", "model_inference":False, "api_tokens":0,
            "report":env.report}
