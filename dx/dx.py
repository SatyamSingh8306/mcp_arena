import os
import sys
import json
import base64
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import argparse

ROOT = Path(__file__).resolve().parent.parent
EVENT_LOG = ROOT / "dx" / "runtime_events.jsonl"
DEPLOY_OUT = ROOT / "dx_deploy"

HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCP Arena DX</title>
<style>
body{font-family:system-ui,Segoe UI,Arial; margin:0; background:#0f1115; color:#e6e6e6}
header{padding:16px 20px; background:#12161e; border-bottom:1px solid #1e2430; display:flex; align-items:center; justify-content:space-between}
.brand{font-weight:700; letter-spacing:.2px}
.grid{display:grid; grid-template-columns: 1fr 1fr; gap:16px; padding:16px}
.card{background:#12161e; border:1px solid #1e2430; border-radius:10px; padding:12px; min-height:150px}
.section-title{font-size:14px; color:#9aa4b2; margin-bottom:8px}
.palette{display:flex; gap:8px; flex-wrap:wrap}
.chip{padding:8px 10px; border-radius:8px; background:#1a1f2b; border:1px dashed #2a3142; cursor:grab; user-select:none}
.canvas{min-height:280px}
.node{padding:10px; border-radius:8px; background:#171c26; border:1px solid #2a3142; margin:6px 0}
.actions{display:flex; gap:8px}
button{background:#1f6feb; color:white; border:0; border-radius:8px; padding:8px 10px; cursor:pointer}
button.secondary{background:#1a1f2b; color:#cbd5e1; border:1px solid #2a3142}
textarea,input{width:100%; background:#0f131a; color:#e6e6e6; border:1px solid #2a3142; border-radius:8px; padding:8px}
.row{display:flex; gap:8px}
.col{flex:1}
.list{max-height:220px; overflow:auto}
.tag{font-size:12px; color:#9aa4b2}
pre{white-space:pre-wrap; word-wrap:break-word; background:#0b0e14; border:1px solid #1e2430; padding:10px; border-radius:8px}
</style></head>
<body>
<header>
  <div class="brand">MCP Arena DX</div>
  <div class="actions">
    <button id="btnExportPy">Export Python</button>
    <button id="btnExportTs" class="secondary">Export TypeScript</button>
    <button id="btnExportJson" class="secondary">Export JSON</button>
  </div>
</header>
<div class="grid">
  <div class="card">
    <div class="section-title">Visual Agent Builder</div>
    <div class="palette">
      <div class="chip" draggable="true" data-type="reflection">Reflection Agent</div>
      <div class="chip" draggable="true" data-type="react">ReAct Agent</div>
      <div class="chip" draggable="true" data-type="planning">Planning Agent</div>
      <div class="chip" draggable="true" data-type="tool">Tool</div>
      <div class="chip" draggable="true" data-type="memory">Memory</div>
      <div class="chip" draggable="true" data-type="policy">Policy</div>
    </div>
    <div id="canvas" class="card canvas" ondragover="event.preventDefault();"></div>
  </div>
  <div class="card">
    <div class="section-title">Config</div>
    <div class="row">
      <div class="col">
        <label class="tag">Agent Type</label>
        <select id="agentType">
          <option value="reflection">reflection</option>
          <option value="react">react</option>
          <option value="planning">planning</option>
        </select>
      </div>
      <div class="col">
        <label class="tag">LLM Identifier</label>
        <input id="llmId" placeholder="e.g., openai:gpt-4o-mini">
      </div>
    </div>
    <div class="row" style="margin-top:8px">
      <div class="col">
        <label class="tag">Memory Type</label>
        <select id="memoryType">
          <option value="conversation">conversation</option>
          <option value="episodic">episodic</option>
        </select>
      </div>
      <div class="col">
        <label class="tag">Max Steps</label>
        <input id="maxSteps" type="number" value="10">
      </div>
    </div>
    <div style="margin-top:8px">
      <label class="tag">Tools</label>
      <div id="tools" class="list"></div>
    </div>
    <div style="margin-top:8px">
      <label class="tag">Policies</label>
      <div id="policies" class="list"></div>
    </div>
  </div>
  <div class="card">
    <div class="section-title">Real-Time Debugging Console</div>
    <div class="row">
      <div class="col"><input id="prompt" placeholder="Enter prompt"></div>
      <div><button id="btnRun">Run</button></div>
      <div><button id="btnReplay" class="secondary">Replay</button></div>
    </div>
    <div id="debugOut" class="list" style="margin-top:8px"></div>
    <div style="margin-top:8px"><span class="tag">Live token/cost</span>
      <div id="cost" class="tag">0 tokens • $0.000</div>
    </div>
  </div>
  <div class="card">
    <div class="section-title">Behavior Visualization</div>
    <div id="graph" style="min-height:240px"></div>
  </div>
  <div class="card">
    <div class="section-title">Templates</div>
    <div id="templates" class="list"></div>
  </div>
  <div class="card">
    <div class="section-title">One-Click Deployment</div>
    <div class="actions">
      <button id="btnDocker">Generate Dockerfile</button>
      <button id="btnCI" class="secondary">Generate CI/CD</button>
    </div>
    <div id="deployOut" style="margin-top:8px"></div>
  </div>
</div>
<script>
const state = { nodes:[], tools:[], policies:[], memory:'conversation', agent:'reflection', maxSteps:10, llm:'' };
const canvas = document.getElementById('canvas');
document.querySelectorAll('.chip').forEach(c=>{
  c.addEventListener('dragstart',e=>{ e.dataTransfer.setData('type', c.dataset.type) })
});
canvas.addEventListener('drop',e=>{
  e.preventDefault();
  const t = e.dataTransfer.getData('type');
  const div = document.createElement('div'); div.className='node'; div.textContent = t;
  canvas.appendChild(div);
  state.nodes.push({type:t});
  if(t==='tool'){ const name = prompt('Tool name'); if(name){ state.tools.push({name}) } }
  if(t==='policy'){ const name = prompt('Policy name'); if(name){ state.policies.push({name}) } }
  drawGraph();
  renderLists();
});
document.getElementById('agentType').onchange = e => { state.agent = e.target.value; drawGraph() };
document.getElementById('memoryType').onchange = e => { state.memory = e.target.value };
document.getElementById('maxSteps').onchange = e => { state.maxSteps = Number(e.target.value) };
document.getElementById('llmId').oninput = e => { state.llm = e.target.value };
function renderLists(){
  const tools = document.getElementById('tools'); tools.innerHTML='';
  state.tools.forEach(t=>{ const n = document.createElement('div'); n.className='node'; n.textContent=t.name; tools.appendChild(n) });
  const pol = document.getElementById('policies'); pol.innerHTML='';
  state.policies.forEach(t=>{ const n = document.createElement('div'); n.className='node'; n.textContent=t.name; pol.appendChild(n) });
}
function estimateTokens(s){ return Math.ceil((s||'').length/4) }
function renderCost(tokens){ const usd = (tokens*0.000002).toFixed(3); document.getElementById('cost').textContent = tokens+' tokens • $'+usd }
function drawGraph(){
  const g = document.getElementById('graph');
  const seq = state.agent==='react' ? ['reason','act','reflect'] :
              state.agent==='planning' ? ['understand','plan','execute','evaluate'] :
              ['generate','reflect','refine'];
  g.innerHTML = '<pre>Flow: '+seq.join(' -> ')+'\\nTools: '+state.tools.map(t=>t.name).join(', ')+'</pre>';
}
function exportPayload(){
  return {
    agentType: state.agent,
    llm: state.llm,
    memoryType: state.memory,
    maxSteps: state.maxSteps,
    tools: state.tools,
    policies: state.policies
  }
}
async function post(path, body){
  const res = await fetch(path,{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  return await res.json();
}
document.getElementById('btnRun').onclick = async ()=>{
  const prompt = document.getElementById('prompt').value;
  const payload = exportPayload(); payload.prompt = prompt;
  const out = document.getElementById('debugOut'); out.innerHTML='';
  const r = await post('/run', payload);
  let tokens = estimateTokens(prompt)+(r.response?r.response.length:0)/4;
  renderCost(Math.ceil(tokens));
  const div = document.createElement('div'); div.className='node'; div.textContent = r.response||'No response';
  out.appendChild(div);
}
document.getElementById('btnReplay').onclick = async ()=>{
  const out = document.getElementById('debugOut'); out.innerHTML='';
  const r = await (await fetch('/replay')).json();
  r.events.slice(-20).forEach(ev=>{ const div = document.createElement('div'); div.className='node'; div.textContent = ev.type+': '+(ev.info||''); out.appendChild(div) });
}
document.getElementById('btnExportPy').onclick = async ()=>{
  const r = await post('/export/python', exportPayload());
  document.body.insertAdjacentHTML('beforeend','<div class=\"card\" style=\"margin:16px\"><div class=\"section-title\">Python Export</div><pre>'+r.code+'</pre></div>')
}
document.getElementById('btnExportTs').onclick = async ()=>{
  const r = await post('/export/typescript', exportPayload());
  document.body.insertAdjacentHTML('beforeend','<div class=\"card\" style=\"margin:16px\"><div class=\"section-title\">TypeScript Export</div><pre>'+r.code+'</pre></div>')
}
document.getElementById('btnExportJson').onclick = async ()=>{
  const r = await post('/export/json', exportPayload());
  document.body.insertAdjacentHTML('beforeend','<div class=\"card\" style=\"margin:16px\"><div class=\"section-title\">JSON Export</div><pre>'+JSON.stringify(r.config,null,2)+'</pre></div>')
}
document.getElementById('btnDocker').onclick = async ()=>{
  const r = await post('/deploy/docker', exportPayload());
  document.getElementById('deployOut').innerHTML = '<pre>'+r.path+'</pre>';
}
document.getElementById('btnCI').onclick = async ()=>{
  const r = await post('/deploy/ci', exportPayload());
  document.getElementById('deployOut').innerHTML = '<pre>'+r.path+'</pre>';
}
drawGraph(); renderLists();
</script></body></html>
""".strip()

class DXHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
            return
        if self.path == "/replay":
            events = []
            if EVENT_LOG.exists():
                with EVENT_LOG.open("r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            events.append(json.loads(line))
                        except Exception:
                            pass
            payload = json.dumps({"events": events})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        return super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        if self.path == "/run":
            resp = run_agent_once(data)
            payload = json.dumps({"response": resp})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        if self.path == "/export/python":
            code = export_python(data)
            payload = json.dumps({"code": code})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        if self.path == "/export/typescript":
            code = export_typescript(data)
            payload = json.dumps({"code": code})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        if self.path == "/export/json":
            payload = json.dumps({"config": data})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        if self.path == "/deploy/docker":
            p = generate_dockerfile(data)
            payload = json.dumps({"path": str(p)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        if self.path == "/deploy/ci":
            p = generate_github_actions(data)
            payload = json.dumps({"path": str(p)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

def write_event(event):
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

def instrument_langgraph():
    try:
        from langgraph.graph.state import StateGraph
    except Exception:
        return
    orig_add_node = StateGraph.add_node
    orig_add_edge = StateGraph.add_edge
    def add_node(self, name, fn):
        def wrapped(state, *args, **kwargs):
            write_event({"type": "node_start", "name": name, "ts": time.time()})
            try:
                result = fn(state, *args, **kwargs)
                write_event({"type": "node_end", "name": name, "ts": time.time()})
                return result
            except Exception as e:
                write_event({"type": "node_error", "name": name, "error": str(e), "ts": time.time()})
                raise
        return orig_add_node(self, name, wrapped)
    def add_edge(self, src, dst):
        write_event({"type": "edge", "src": src, "dst": dst, "ts": time.time()})
        return orig_add_edge(self, src, dst)
    StateGraph.add_node = add_node
    StateGraph.add_edge = add_edge

def create_agent_from_payload(payload):
    agent_type = payload.get("agentType") or payload.get("agent_type") or "reflection"
    memory_type = payload.get("memoryType", "conversation")
    llm = None
    try:
        llm = payload.get("llm")
    except Exception:
        llm = None
    try:
        from mcp_arena.agent.factory import AgentFactory
    except Exception:
        return None
    factory = AgentFactory()
    cfg = {"memory_type": memory_type}
    if llm:
        cfg["llm"] = llm
    try:
        agent = factory.create_agent(agent_type, cfg)
    except Exception:
        agent = None
    return agent

def run_agent_once(payload):
    instrument_langgraph()
    prompt = payload.get("prompt") or ""
    agent = create_agent_from_payload(payload)
    if not agent:
        write_event({"type": "error", "info": "agent_unavailable", "ts": time.time()})
        return ""
    try:
        result = agent.process(prompt)
        write_event({"type": "response", "info": str(result)[:500], "ts": time.time()})
        return str(result)
    except Exception as e:
        write_event({"type": "error", "info": str(e), "ts": time.time()})
        return f"Error: {e}"

def export_python(payload):
    agent_type = payload.get("agentType", "reflection")
    memory_type = payload.get("memoryType", "conversation")
    llm = payload.get("llm", "")
    tools = payload.get("tools", [])
    policies = payload.get("policies", [])
    lines = []
    lines.append("from mcp_arena.agent import AgentFactory")
    lines.append("")
    lines.append("factory = AgentFactory()")
    cfg = {"memory_type": memory_type}
    if llm:
        cfg["llm"] = llm
    lines.append(f'agent = factory.create_agent("{agent_type}", {json.dumps(cfg)})')
    if tools:
        lines.append("")
        lines.append("# add tools")
        for t in tools:
            lines.append(f'# agent.add_tool({t.get("name","")})')
    if policies:
        lines.append("")
        lines.append("# add policies")
        for p in policies:
            lines.append(f'# agent.add_policy({p.get("name","")})')
    lines.append("")
    lines.append('resp = agent.process("YOUR_PROMPT")')
    lines.append("print(resp)")
    return "\n".join(lines)

def export_typescript(payload):
    agent_type = payload.get("agentType", "reflection")
    memory_type = payload.get("memoryType", "conversation")
    llm = payload.get("llm", "")
    code = f"""
// MCP Arena DX TypeScript export
export const config = {{
  agentType: "{agent_type}",
  memoryType: "{memory_type}",
  llm: "{llm}"
}};
""".strip()
    return code

def generate_dockerfile(payload):
    DEPLOY_OUT.mkdir(parents=True, exist_ok=True)
    dockerfile = DEPLOY_OUT / "Dockerfile"
    content = f"""
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .
CMD ["python","-c","print('MCP Arena DX container');"]
""".strip()
    dockerfile.write_text(content, encoding="utf-8")
    return dockerfile

def generate_github_actions(payload):
    DEPLOY_OUT.mkdir(parents=True, exist_ok=True)
    wf = DEPLOY_OUT / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    yml = wf / "ci.yml"
    content = """
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install
        run: pip install .[dev]
      - name: Lint
        run: python -m pip install black isort mypy && black . --check && isort . --check-only && mypy .
      - name: Tests
        run: pytest -q
""".strip()
    yml.write_text(content, encoding="utf-8")
    return yml

def start_server(host: str = "127.0.0.1", port: int = 8000):
    server = HTTPServer((host, port), DXHandler)
    print(f"DX server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

def main():
    parser = argparse.ArgumentParser(description="MCP Arena DX")
    sub = parser.add_subparsers(dest="cmd")
    p_builder = sub.add_parser("builder")
    p_builder.add_argument("--host", default="127.0.0.1")
    p_builder.add_argument("--port", type=int, default=8000)
    p_debug = sub.add_parser("debug")
    p_debug.add_argument("--agent", default="reflection")
    p_debug.add_argument("--memory", default="conversation")
    p_debug.add_argument("--prompt", default="Hello")
    p_templates = sub.add_parser("templates")
    p_deploy = sub.add_parser("deploy")
    args = parser.parse_args()
    if args.cmd == "builder":
        start_server(args.host, args.port)
    elif args.cmd == "debug":
        payload = {"agentType": args.agent, "memoryType": args.memory, "prompt": args.prompt}
        print("Starting debug session")
        resp = run_agent_once(payload)
        print("Response:")
        print(str(resp))
        if EVENT_LOG.exists():
            print("Timeline:")
            with EVENT_LOG.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        ev = json.loads(line)
                        label = f"{ev.get('type')} {ev.get('name','')}"
                        print(label)
                    except Exception:
                        pass
    elif args.cmd == "templates":
        tpl = [
            {"name":"Support Bot","agent":"reflection","tools":["SearchTool"],"policies":["SafetyPolicy"]},
            {"name":"Code Reviewer","agent":"react","tools":["FileSystemTool","WebTool"],"policies":["ContentFilterPolicy"]},
            {"name":"Analyst","agent":"planning","tools":["DataAnalysisTool"],"policies":["ToolUsagePolicy"]}
        ]
        for t in tpl:
            print(f"{t['name']} | {t['agent']} | Tools: {', '.join(t['tools'])} | Policies: {', '.join(t['policies'])}")
    elif args.cmd == "deploy":
        p1 = generate_dockerfile({})
        p2 = generate_github_actions({})
        print("Generated:")
        print(p1)
        print(p2)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
