import json
from pathlib import Path
from omnioperator.workflow import run_workflow

if __name__=='__main__':
    manifest=json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
    result=run_workflow('data/AirQualityUCI.csv','reports/sensor-quality.json',manifest['sha256'])
    print(json.dumps({k:v for k,v in result.items() if k!='report'},indent=2))
    raise SystemExit(0 if result['success'] else 1)
