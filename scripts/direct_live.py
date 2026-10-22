"""Run frozen development probes against an owned local model endpoint."""
import argparse
import json
import platform
import time
from pathlib import Path
from datetime import datetime, timezone
from omnioperator.direct_tools import DatasetTools, DirectToolAdapter, run


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports/direct-live-lifecycle.json'))
    parser.add_argument('--model-manifest', type=Path)
    parser.add_argument('--endpoint', default='http://127.0.0.1:8081/v1/chat/completions')
    args = parser.parse_args()
    # Preserve evidence rather than silently replacing a previous run.
    if args.output.exists():
        raise FileExistsError(f'Result already exists: {args.output}')
    cases_path = Path('data/direct-cases.json')
    cases = json.loads(cases_path.read_text(encoding='utf-8'))['cases']
    manifest = json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
    rows = []
    for case in cases:
        output = Path('reports/direct-runs') / (case['id']+'-'+str(time.time_ns())+'.json')
        tools = DatasetTools('data/AirQualityUCI.csv', output, manifest['sha256'],
                             allow_export=case['expected']=='export')
        result = run(DirectToolAdapter(endpoint=args.endpoint), tools, case['goal'], case['expected'])
        result.update({'case':case['id'], 'goal':case['goal'], 'expected':case['expected']})
        rows.append(result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('history','model_responses')},ensure_ascii=True),flush=True)
    import hashlib
    report = {'checked_at':datetime.now(timezone.utc).isoformat(),
              'kind':'real local inference; constrained lifecycle; repeated development cases',
              'python':platform.python_version(), 'source_sha256':manifest['sha256'],
              'cases_sha256':hashlib.sha256(cases_path.read_bytes()).hexdigest(),
              'cases':rows, 'passed':sum(r['success'] for r in rows), 'total':len(rows),
              'note':'Write capability supplied by harness, not inferred by model. Not an independent holdout.'}
    if args.model_manifest:
        report['model_manifest'] = json.loads(args.model_manifest.read_text(encoding='utf-8'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
