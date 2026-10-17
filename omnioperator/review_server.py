"""Read-only loopback report viewer. Run the workflow first."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>OmniOperator | Sensor review</title>
<style>body{margin:0;background:#f4f1e9;color:#23342f;font:17px Georgia,serif}main{max-width:980px;margin:auto;padding:36px 22px}h1{font-size:42px;margin:8px 0}small{font:13px monospace}section{border-top:1px solid #9da89a;margin-top:26px;padding-top:20px}.stats{display:flex;gap:40px;flex-wrap:wrap}.stats strong{font-size:30px;display:block}table{border-collapse:collapse;width:100%;font:14px monospace}td,th{padding:10px 6px;text-align:left;border-bottom:1px solid #ccd0c4}.overflow{overflow:auto}code{overflow-wrap:anywhere}a{color:#255c47}</style>
<main><small>OMNIOPERATOR / EXECUTION EVIDENCE</small><h1>Sensor data review</h1><p>A real-file workflow with verified output. Fixed planner; no model inference or desktop control.</p>
<div id="status" role="status">Loading report…</div><section><div class="stats" id="stats"></div></section><section><h2>Missing observations</h2><p>UCI uses −200 for missing values. These values are excluded from means.</p><div class="overflow"><table><thead><tr><th>Channel</th><th>Valid</th><th>Missing</th><th>Missing %</th><th>Mean</th></tr></thead><tbody id="rows"></tbody></table></div></section><section><h2>Provenance</h2><p>Source: <a href="https://doi.org/10.24432/C59K5F">Saverio Vito, UCI Air Quality</a>. Historical research data, not a live sensor feed.</p><p>Input SHA-256: <code id="hash"></code></p><p id="dates"></p><p>CSV contains 9,357 populated records and 114 empty lines; UCI's page lists 9,358 instances. Raw file dates are retained without adjusting them to the description.</p></section></main>
<script src="/app.js"></script></html>"""
JS = """fetch('/api/report').then(r=>{if(!r.ok)throw Error('Report unavailable');return r.json()}).then(r=>{document.getElementById('status').textContent='Verified local report · '+r.rows.toLocaleString()+' records';for(const [label,value] of [['Records',r.rows],['Channels',Object.keys(r.columns).length],['Blank rows',r.blank_rows_skipped]]){const d=document.createElement('div'),s=document.createElement('strong');s.textContent=value.toLocaleString();d.append(s,document.createTextNode(label));document.getElementById('stats').append(d)}for(const [name,c]of Object.entries(r.columns)){const tr=document.createElement('tr');for(const x of [name,c.valid,c.missing,c.missing_percent,c.mean]){const td=document.createElement('td');td.textContent=x===null?'—':String(x);tr.append(td)}document.getElementById('rows').append(tr)}document.getElementById('hash').textContent=r.source_sha256;document.getElementById('dates').textContent=r.start+' → '+r.end}).catch(e=>document.getElementById('status').textContent=e.message);"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}:
            self.send_error(403); return
        if self.path == '/':
            content, mime = HTML.encode(), 'text/html; charset=utf-8'
        elif self.path == '/app.js':
            content, mime = JS.encode(), 'text/javascript; charset=utf-8'
        elif self.path == '/api/report':
            try:
                content=(ROOT/'reports/sensor-quality.json').read_bytes()
            except FileNotFoundError:
                self.send_error(503); return
            mime='application/json'
        else:
            self.send_error(404); return
        self.send_response(200)
        self.send_header('Content-Type',mime)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'")
        self.send_header('Content-Length',str(len(content)))
        self.end_headers(); self.wfile.write(content)
    def log_message(self,*args):
        pass

def serve(port=8793):
    server=HTTPServer(('127.0.0.1',port),Handler)
    print(f'Review: http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    finally: server.server_close()

if __name__ == '__main__':
    serve()
