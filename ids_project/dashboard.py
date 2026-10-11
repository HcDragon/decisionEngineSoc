"""Minimal live IDS dashboard. No framework — stdlib http.server.

  python dashboard.py        # then open http://localhost:8080

Serves one page that polls /events (the JSON-lines events.log engine.py writes).
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG_FILE = "events.log"
PORT = 8080

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>IDS Monitor</title>
<style>
 body{font-family:system-ui,sans-serif;background:#0f1115;color:#e6e6e6;margin:0;padding:24px}
 h1{font-size:20px;margin:0 0 4px} .sub{color:#8a94a6;font-size:13px;margin-bottom:16px}
 .stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
 .card{background:#1a1e27;border:1px solid #2a2f3a;border-radius:8px;padding:12px 16px;min-width:90px}
 .card b{font-size:22px;display:block} .card span{color:#8a94a6;font-size:12px}
 table{width:100%;border-collapse:collapse;font-size:14px}
 th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #2a2f3a}
 th{color:#8a94a6;font-weight:600} tr:hover{background:#161a22}
 .pill{padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600}
 .blocked{background:#3a1416;color:#ff8a8a} .would{background:#3a2e14;color:#ffd27a}
 .fail{background:#2a2f3a;color:#8a94a6}
</style></head><body>
<h1>Intrusion Detection — Live Feed</h1>
<div class="sub">AI/ML engine · auto-refresh 2s</div>
<div class="stats">
 <div class="card"><b id="total">0</b><span>detections</span></div>
 <div class="card"><b id="blocked">0</b><span>blocked</span></div>
 <div class="card"><b id="ips">0</b><span>unique IPs</span></div>
</div>
<table><thead><tr><th>Time</th><th>Attack</th><th>Confidence</th><th>Source IP</th><th>Action</th></tr></thead>
<tbody id="rows"></tbody></table>
<script>
const cls={blocked:'blocked','would-block':'would','block-failed':'fail'};
async function tick(){
 const ev=await (await fetch('/events')).json();
 document.getElementById('total').textContent=ev.length;
 document.getElementById('blocked').textContent=ev.filter(e=>e.action==='blocked').length;
 document.getElementById('ips').textContent=new Set(ev.map(e=>e.src_ip)).size;
 document.getElementById('rows').innerHTML=ev.slice().reverse().map(e=>
  `<tr><td>${e.time}</td><td>${e.attack}</td><td>${(e.confidence*100).toFixed(0)}%</td>`+
  `<td>${e.src_ip}</td><td><span class="pill ${cls[e.action]||''}">${e.action}</span></td></tr>`
 ).join('');
}
tick();setInterval(tick,2000);
</script></body></html>"""


def read_events():
    out = []
    try:
        with open(LOG_FILE) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except FileNotFoundError:
        pass
    return out


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/events"):
            body = json.dumps(read_events()).encode()
            ctype = "application/json"
        else:
            body = PAGE.encode()
            ctype = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Dashboard: http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
