"""Real CSV + independent pandas oracle + actual loopback HTTP requests."""
import hashlib, json, platform, threading, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from http.server import HTTPServer
import pandas as pd
from omnioperator.workflow import run_workflow
from omnioperator.review_server import Handler

manifest=json.loads(Path('data/manifest.json').read_text(encoding='utf-8'))
result=run_workflow('data/AirQualityUCI.csv','reports/sensor-quality.json',manifest['sha256'])
assert result['success']
report=result['report']
frame=pd.read_csv('data/AirQualityUCI.csv',sep=';',decimal=',').dropna(subset=['Date','Time'])
assert len(frame)==report['rows']==9357
for name, stats in report['columns'].items():
    col=pd.to_numeric(frame[name],errors='raise').replace(-200,float('nan'))
    assert int(col.isna().sum())==stats['missing']
    assert abs(float(col.mean())-stats['mean'])<0.000001
server=HTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
http=[]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    for path,expected in [('/',200),('/app.js',200),('/api/report',200),('/../LICENSE',404)]:
        try:
            with opener.open('http://127.0.0.1:'+str(server.server_port)+path,timeout=10) as response:
                status=response.status;body=response.read()
        except urllib.error.HTTPError as exc:
            status=exc.code;body=b''
        assert status==expected
        if path=='/api/report': assert json.loads(body)==report
        http.append({'path':path,'status':status})
finally:
    server.shutdown();server.server_close();thread.join(timeout=5)
result.update({'checked_at':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
 'independent_oracle':'pandas '+pd.__version__+'; all 13 numeric columns checked', 'http_checks':http})
Path('reports/real-workflow.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='report'},indent=2))
