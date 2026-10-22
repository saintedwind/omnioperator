"""Run against a separately started local model. Does not download/start one."""
import hashlib,json,platform,time
from pathlib import Path
from datetime import datetime,timezone
from omnioperator.adapters.local_model import LocalModelAdapter
from omnioperator.core.agent import Agent
from omnioperator.workflow import DatasetWorkspace,analyze

manifest=json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
rows=[]
for case,goal,wants_export in [
    ('export','Inspect the sensor dataset and export the quality report.',True),
    ('inspect','Inspect the sensor dataset only. Do not export a report.',False),
    ('paraphrase','Check missing readings in the source CSV, then save the analysis.',True)]:
    output=Path('reports/model-runs')/(case+'-'+str(time.time_ns())+'.json')
    env=DatasetWorkspace('data/AirQualityUCI.csv',output,manifest['sha256'])
    adapter=LocalModelAdapter()
    def verifier(env,goal):
        if wants_export:
            return env.status=='Export complete' and env.output.is_file() and json.loads(env.output.read_text())==analyze(env.source.read_bytes())
        return env.report is not None and not env.output.exists()
    episode=Agent(env,adapter,max_steps=9,step_budget_seconds=180,verifier=verifier).run(goal)
    row={'case':case,'goal':goal,'success':episode.success,'stop_reason':episode.stop_reason,
         'steps':episode.n_steps,'latency_ms':episode.total_latency_ms,'tokens':episode.tokens_used,
         'actions':[{'action':s.action,'params':s.params,'ok':s.result.success if s.result else None} for s in episode.steps],
         'model_responses':adapter.responses,'exported':output.is_file()}
    rows.append(row)
    print(json.dumps({k:v for k,v in row.items() if k not in ('actions','model_responses') }),flush=True)
report={'checked_at':datetime.now(timezone.utc).isoformat(),'kind':'real local model inference on real file backend; no GUI control',
        'python':platform.python_version(),'dataset_sha256':manifest['sha256'],'cases':rows,
        'passed':sum(r['success'] for r in rows),'total':len(rows)}
Path('reports/live-model.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
