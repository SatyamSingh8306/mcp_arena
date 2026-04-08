"""
Visual dashboard for MCP server status and metrics.

Serves a lightweight HTML dashboard on a local port that polls
the /metrics JSON endpoint for real-time updates.
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_arena.mcp.metrics import MetricsCollector


# ---------------------------------------------------------------------------
# HTML template – single-page dashboard (no external dependencies)
# ---------------------------------------------------------------------------

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{server_name} — Dashboard</title>
<style>
:root {
  --bg: #0f1117;
  --card: #1a1d27;
  --border: #2a2d3a;
  --text: #e4e4e7;
  --muted: #9ca3af;
  --accent: #6366f1;
  --accent-light: #818cf8;
  --green: #22c55e;
  --red: #ef4444;
  --yellow: #eab308;
  --blue: #3b82f6;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  padding: 24px;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
  flex-wrap: wrap;
  gap: 12px;
}
.header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent-light);
}
.header .badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.badge-online { background: rgba(34,197,94,.15); color: var(--green); border: 1px solid rgba(34,197,94,.3); }
.badge-offline { background: rgba(239,68,68,.15); color: var(--red); border: 1px solid rgba(239,68,68,.3); }

/* Stat cards row */
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}
.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  transition: border-color .2s;
}
.stat-card:hover { border-color: var(--accent); }
.stat-card .label {
  font-size: 0.75rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}
.stat-card .value {
  font-size: 1.75rem;
  font-weight: 700;
}
.stat-card .sub { font-size: 0.8rem; color: var(--muted); margin-top: 4px; }
.value-green { color: var(--green); }
.value-red { color: var(--red); }
.value-blue { color: var(--blue); }
.value-yellow { color: var(--yellow); }
.value-accent { color: var(--accent-light); }

/* Sections */
.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--accent-light);
  margin-bottom: 14px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}

/* Tool table */
.tool-table-wrap {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 28px;
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
th {
  text-align: left;
  padding: 10px 12px;
  color: var(--muted);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(99,102,241,.05); }
.bar-cell { width: 140px; }
.bar-bg {
  background: var(--border);
  border-radius: 4px;
  height: 8px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--accent);
  transition: width .4s ease;
}
.error-bar .bar-fill { background: var(--red); }

/* Recent log */
.log-wrap {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 28px;
  max-height: 340px;
  overflow-y: auto;
}
.log-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  font-size: 0.82rem;
  border-bottom: 1px solid rgba(42,45,58,.5);
}
.log-entry:last-child { border-bottom: none; }
.log-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-ok { background: var(--green); }
.dot-err { background: var(--red); }
.log-time { color: var(--muted); min-width: 80px; }
.log-tool { color: var(--accent-light); font-weight: 600; }
.log-latency { color: var(--muted); margin-left: auto; }
.log-error-msg { color: var(--red); font-size: 0.78rem; }

/* Footer */
.footer {
  text-align: center;
  color: var(--muted);
  font-size: 0.75rem;
  margin-top: 20px;
}
.footer a { color: var(--accent-light); text-decoration: none; }
.footer a:hover { text-decoration: underline; }

/* Pulse animation for live indicator */
.pulse {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green);
  margin-right: 6px;
  animation: pulse-anim 2s infinite;
}
@keyframes pulse-anim {
  0%,100% { opacity: 1; }
  50% { opacity: .4; }
}
</style>
</head>
<body>

<div class="header">
  <h1 id="serverName">{server_name}</h1>
  <div>
    <span class="pulse"></span>
    <span class="badge badge-online" id="statusBadge">ONLINE</span>
  </div>
</div>

<!-- Stat cards -->
<div class="stats">
  <div class="stat-card">
    <div class="label">Uptime</div>
    <div class="value value-accent" id="uptime">—</div>
  </div>
  <div class="stat-card">
    <div class="label">Total Requests</div>
    <div class="value value-blue" id="totalReqs">0</div>
  </div>
  <div class="stat-card">
    <div class="label">Active Connections</div>
    <div class="value value-green" id="activeConns">0</div>
  </div>
  <div class="stat-card">
    <div class="label">Total Errors</div>
    <div class="value value-red" id="totalErrors">0</div>
  </div>
  <div class="stat-card">
    <div class="label">Error Rate</div>
    <div class="value value-yellow" id="errorRate">0%</div>
  </div>
  <div class="stat-card">
    <div class="label">Tools Registered</div>
    <div class="value value-accent" id="toolCount">0</div>
  </div>
</div>

<!-- Tool usage table -->
<div class="tool-table-wrap">
  <div class="section-title">Tool Usage</div>
  <table>
    <thead>
      <tr>
        <th>Tool</th>
        <th>Calls</th>
        <th class="bar-cell">Usage</th>
        <th>Errors</th>
        <th class="bar-cell">Error Rate</th>
        <th>Avg Latency</th>
      </tr>
    </thead>
    <tbody id="toolTableBody">
      <tr><td colspan="6" style="color:var(--muted);text-align:center">No tool data yet</td></tr>
    </tbody>
  </table>
</div>

<!-- Recent requests -->
<div class="log-wrap">
  <div class="section-title">Recent Requests</div>
  <div id="recentLog">
    <div style="color:var(--muted);text-align:center;padding:16px 0">Waiting for requests…</div>
  </div>
</div>

<div class="footer">
  Powered by <a href="https://github.com/SatyamSingh8306/mcp_arena" target="_blank">MCP Arena</a>
  &middot; Refreshes every 2 s
</div>

<script>
const POLL_INTERVAL = 2000;

function fmt(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

async function poll() {
  try {
    const res = await fetch('/metrics');
    if (!res.ok) throw new Error(res.statusText);
    const m = await res.json();
    update(m);
    document.getElementById('statusBadge').textContent = 'ONLINE';
    document.getElementById('statusBadge').className = 'badge badge-online';
  } catch {
    document.getElementById('statusBadge').textContent = 'OFFLINE';
    document.getElementById('statusBadge').className = 'badge badge-offline';
  }
}

function update(m) {
  document.getElementById('uptime').textContent = m.uptime_formatted;
  document.getElementById('totalReqs').textContent = m.total_requests.toLocaleString();
  document.getElementById('activeConns').textContent = m.active_connections;
  document.getElementById('totalErrors').textContent = m.total_errors.toLocaleString();
  document.getElementById('errorRate').textContent = (m.error_rate * 100).toFixed(1) + '%';
  document.getElementById('toolCount').textContent = m.tools_registered;

  // Tool table
  const tbody = document.getElementById('toolTableBody');
  const tools = Object.entries(m.tools);
  if (tools.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted);text-align:center">No tool data yet</td></tr>';
  } else {
    const maxCalls = Math.max(...tools.map(([,v]) => v.calls), 1);
    tbody.innerHTML = tools.map(([name, t]) => {
      const errRate = t.calls > 0 ? ((t.errors / t.calls) * 100).toFixed(1) : '0.0';
      const callPct = ((t.calls / maxCalls) * 100).toFixed(0);
      return `<tr>
        <td><strong>${name}</strong></td>
        <td>${t.calls}</td>
        <td class="bar-cell"><div class="bar-bg"><div class="bar-fill" style="width:${callPct}%"></div></div></td>
        <td style="color:${t.errors > 0 ? 'var(--red)' : 'var(--muted)'}">${t.errors}</td>
        <td class="bar-cell error-bar"><div class="bar-bg"><div class="bar-fill" style="width:${errRate}%"></div></div></td>
        <td>${t.avg_latency_s > 0 ? t.avg_latency_s.toFixed(3) + ' s' : '—'}</td>
      </tr>`;
    }).join('');
  }

  // Recent log
  const logDiv = document.getElementById('recentLog');
  const recent = m.recent_requests || [];
  if (recent.length === 0) {
    logDiv.innerHTML = '<div style="color:var(--muted);text-align:center;padding:16px 0">Waiting for requests…</div>';
  } else {
    logDiv.innerHTML = recent.slice().reverse().map(r => {
      const errMsg = r.metadata && r.metadata.error ? `<span class="log-error-msg">${r.metadata.error}</span>` : '';
      const lat = r.latency !== undefined ? `<span class="log-latency">${r.latency.toFixed(3)}s</span>` : '';
      return `<div class="log-entry">
        <span class="log-dot ${r.success ? 'dot-ok' : 'dot-err'}"></span>
        <span class="log-time">${fmt(r.timestamp)}</span>
        <span class="log-tool">${r.tool}</span>
        ${errMsg}
        ${lat}
      </div>`;
    }).join('');
  }
}

setInterval(poll, POLL_INTERVAL);
poll();
</script>
</body>
</html>"""


class _DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard and metrics endpoint."""

    # Set by DashboardServer before starting
    metrics_collector: Optional["MetricsCollector"] = None
    server_name: str = "MCP Server"

    def do_GET(self):
        if self.path == "/metrics":
            self._serve_metrics()
        elif self.path in ("/", "/dashboard"):
            self._serve_dashboard()
        else:
            self.send_error(404, "Not Found")

    def _serve_metrics(self):
        """Serve metrics as JSON."""
        if self.metrics_collector is None:
            self.send_error(503, "Metrics not available")
            return
        data = json.dumps(self.metrics_collector.get_metrics())
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.end_headers()
        self.wfile.write(data.encode())

    def _serve_dashboard(self):
        """Serve the HTML dashboard page."""
        html = DASHBOARD_HTML.replace("{server_name}", self.server_name)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    # Suppress default logging to stderr
    def log_message(self, format, *args):
        pass


class DashboardServer:
    """Lightweight HTTP server that serves the metrics dashboard.
    
    Runs in a daemon thread so it doesn't block the main MCP server.
    Binds only to localhost for security.
    
    Example:
        >>> from mcp_arena.mcp.metrics import MetricsCollector
        >>> from mcp_arena.mcp.dashboard import DashboardServer
        >>>
        >>> metrics = MetricsCollector("My Server")
        >>> dashboard = DashboardServer(metrics, port=9090)
        >>> dashboard.start()
        >>> # Dashboard is now at http://127.0.0.1:9090/dashboard
        >>> # Metrics JSON at   http://127.0.0.1:9090/metrics
    """

    def __init__(
        self,
        metrics_collector: "MetricsCollector",
        host: str = "127.0.0.1",
        port: int = 9090,
        server_name: str = "MCP Server",
    ):
        """Initialize the dashboard server.
        
        Args:
            metrics_collector: The MetricsCollector instance to expose.
            host: Host to bind to (default localhost only).
            port: Port for the dashboard HTTP server.
            server_name: Display name shown in the dashboard UI.
        """
        self.metrics_collector = metrics_collector
        self.host = host
        self.port = port
        self.server_name = server_name
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        """Dashboard URL."""
        return f"http://{self.host}:{self.port}/dashboard"

    @property
    def metrics_url(self) -> str:
        """Metrics JSON endpoint URL."""
        return f"http://{self.host}:{self.port}/metrics"

    @property
    def is_running(self) -> bool:
        """Whether the dashboard server is currently running."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the dashboard server in a background daemon thread."""
        if self.is_running:
            return

        # Inject dependencies into the handler class
        handler_class = type(
            "_BoundHandler",
            (_DashboardHandler,),
            {
                "metrics_collector": self.metrics_collector,
                "server_name": self.server_name,
            },
        )

        self._httpd = HTTPServer((self.host, self.port), handler_class)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name=f"dashboard-{self.port}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the dashboard server."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd = None
        self._thread = None
