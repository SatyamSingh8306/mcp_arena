# Frequently Asked Questions (FAQ)

Common questions and answers about **mcp_arena**.

---

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Integration](#integration)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Which preset should I install?

Install only the presets you need. Each preset has its own optional dependency group:

```bash
# Single preset
pip install mcp-arena[github]

# Multiple presets
pip install mcp-arena[github,slack,postgres]

# Everything
pip install mcp-arena[all]
```

Available groups: `github`, `gitlab`, `bitbucket`, `slack`, `whatsapp`, `gmail`, `outlook`, `postgres`, `mongodb`, `redis`, `docker`, `kubernetes`, `local_operation`, `vectordb`, `agents`.

There are also convenience bundles:
- `communication` — Gmail + Outlook + Slack + WhatsApp
- `messaging` — Slack + WhatsApp
- `email` — Gmail + Outlook
- `all` — every preset and agent
- `complete` — everything + dev tools (pytest, black, ruff, etc.)

---

### Do I need all dependencies?

No. The core package installs a broad set of dependencies, but you can install only what you need using optional groups (see above). If you only use the GitHub preset, `pip install mcp-arena[github]` is sufficient.

---

### What Python version is required?

**Python 3.12 or higher** is required. Check your version:

```bash
python --version
```

If you need to upgrade, download from [python.org](https://www.python.org/downloads/) or use `pyenv`:

```bash
pyenv install 3.12
pyenv local 3.12
```

---

### How do I resolve `pip install` errors?

Common install issues and fixes:

| Error | Solution |
|---|---|
| `pg_config executable not found` | Install PostgreSQL dev headers: `sudo apt-get install libpq-dev` (Linux) or `brew install postgresql` (macOS) |
| `Could not find a version that satisfies the requirement` | Upgrade pip: `pip install --upgrade pip` |
| Installation hangs on `sentence-transformers` | PyTorch is a large download (~2 GB). If you don't need local embeddings, skip `vectordb` extras |
| `ERROR: mcp-arena requires Python >=3.12` | Upgrade Python to 3.12+ |
| Permission errors | Use `pip install --user mcp-arena` or use a virtual environment |

Using a virtual environment is always recommended:

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
pip install mcp-arena[all]
```

---

## Usage

### Can I use multiple servers together?

Yes. There are two main ways:

**1. MCPLangChainIntegration** — chain multiple servers into a single LangChain agent:

```python
from mcp_arena.wrapper.langchain_integration import MCPLangChainIntegration
from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key="...")

integration = MCPLangChainIntegration(llm=llm)
integration.add_github_server(token="ghp_...")
integration.add_slack_server(bot_token="xoxb-...")
integration.initialize()

# The agent now has tools from BOTH servers
result = integration.invoke("List my GitHub repos and post a summary to #general on Slack")
integration.shutdown()
```

**2. MCPLangChainWrapper** — add servers by config or instance:

```python
from mcp_arena.wrapper.langchain_wrapper import MCPLangChainWrapper

wrapper = MCPLangChainWrapper()
wrapper.add_server("github", github_server, transport="stdio")
wrapper.add_server("slack", slack_server, transport="stdio")
wrapper.connect()
agent = wrapper.create_agent(llm=llm)
```

Both approaches merge tools from all servers into a single agent that can call any tool from any server.

---

### How do I switch between agents?

Use the `AgentFactory` or `AgentRouter`:

**Creating different agent types:**

```python
from mcp_arena.agent.factory import AgentFactory

factory = AgentFactory()

# Available types: "reflection", "react", "planning"
reflection_agent = factory.create_agent("reflection")
react_agent = factory.create_agent("react", config={"max_steps": 20})
planning_agent = factory.create_agent("planning")
```

**Automatic routing based on query:**

```python
from mcp_arena.agent.router import create_default_router

router = create_default_router()

# Routes automatically:
# "plan/step/goal/how to" → PlanningAgent
# "do/execute/run/search"  → ReactAgent
# Everything else          → ReflectionAgent
agent_type = router.route("How do I build a REST API?")
```

**Custom routing with SmartRouter (LLM-based):**

```python
from mcp_arena.agent.router import SmartRouter

router = SmartRouter(llm=llm)
agent_type = router.route("Analyze the sales data and create a report")
```

---

### What's the difference between presets and custom servers?

**Presets** are ready-made MCP servers for popular services (GitHub, Slack, PostgreSQL, etc.). They extend `BaseMCPServer` with pre-configured tools specific to that service.

```python
from mcp_arena.presents.github import GithubMCPServer

# Ready to use — all GitHub tools are pre-registered
server = GithubMCPServer(token="ghp_...")
server.run()
```

**Custom servers** are servers you build yourself by subclassing `BaseMCPServer`:

```python
from mcp_arena.mcp.server import BaseMCPServer

class MyCustomServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp_server.tool()
        def my_tool(query: str) -> str:
            """My custom tool."""
            return f"Result for: {query}"

server = MyCustomServer(name="My Server", description="A custom MCP server")
server.run()
```

The key difference: presets give you a fully functional server out of the box, while custom servers let you register your own tools for any use case.

---

### What agent types are available?

Three built-in agent types:

| Type | Class | Best For | Default Config |
|---|---|---|---|
| `"reflection"` | `ReflectionAgent` | Iterative self-improvement, reasoning | `max_reflections=3`, conversation memory |
| `"react"` | `ReactAgent` | Tool-using tasks, action-oriented work | `max_steps=10`, conversation memory |
| `"planning"` | `PlanningAgent` | Multi-step goal decomposition | Episodic memory |

You can also register custom agent types:

```python
from mcp_arena.agent.factory import AgentFactory

factory = AgentFactory()
factory.register_agent_type("my_agent", MyCustomAgentClass)
```

---

### What transport types are supported?

Three transports:

| Transport | Default | When to Use |
|---|---|---|
| `stdio` | **Yes** | Local process communication (most common) |
| `sse` | No | Server-Sent Events over HTTP — browser-accessible |
| `streamable-http` | No | HTTP streaming — best for production deployments |

```python
# stdio (default)
server.run()

# SSE — accessible at http://host:port/sse
server.run(transport="sse")

# Streamable HTTP — accessible at http://host:port/mcp
server.run(transport="streamable-http")
```

---

### How do I use the CLI?

The CLI is available as `mcp-arena` or `mcp_arena` after installation:

```bash
# List all available presets
mcp-arena list

# Get details about a specific preset
mcp-arena info github

# Run a server
mcp-arena run --mcp-server github --token ghp_...

# Validate a server configuration
mcp-arena validate github

# Show project info
mcp-arena about
```

Pass extra arguments to the server with `--key value`:

```bash
mcp-arena run --mcp-server postgres --connection_string "postgresql://user:pass@localhost/db"
```

---

### How do I use pre-built agent configurations?

The `AgentRegistry` provides named configurations for common use cases:

```python
from mcp_arena.agent.factory import AgentRegistry

registry = AgentRegistry()
registry.setup_default_configs()

# Available configs: "basic_reflection", "tool_react", "advanced_planning", "research"
agent = registry.create_from_config("tool_react")
```

Or use the builder pattern for fine-grained control:

```python
from mcp_arena.agent.factory import AgentBuilder

agent = (AgentBuilder("react")
         .with_config(max_steps=25)
         .with_memory("conversation")
         .with_llm(my_llm)
         .with_tool(my_tool)
         .build())
```

---

## Integration

### Can I use this with LangChain?

Yes — LangChain integration is a first-class feature. There are two integration paths:

**1. MCPLangChainIntegration** (recommended):

```python
from mcp_arena.wrapper.langchain_integration import MCPLangChainIntegration
from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key="...")

integration = MCPLangChainIntegration(llm=llm)
integration.add_github_server(token="ghp_...")
integration.initialize()

result = integration.invoke("List open issues in my repo")
integration.shutdown()
```

**2. One-liner with `create_github_agent`:**

```python
from mcp_arena.wrapper.langchain_integration import create_github_agent

agent = create_github_agent(token="ghp_...", llm=llm)
```

The integration uses `langchain-mcp-adapters` under the hood to bridge MCP tools into the LangChain ecosystem.

---

### How do I integrate with existing Python projects?

mcp_arena servers are regular Python objects. Import and use them directly:

```python
from mcp_arena.presents.github import GithubMCPServer

# Create the server
server = GithubMCPServer(token="ghp_...")

# Use tools directly without running the server
# (tools are registered and callable as Python functions)
tools = server.get_registered_tools()
print(f"Available tools: {tools}")

# Or run the server for MCP client connections
server.run(transport="sse")  # Non-blocking HTTP server
```

You can also wrap servers for agent use:

```python
from mcp_arena.wrapper.agent_wrapper import MCPAgentWrapper

wrapper = MCPAgentWrapper(server)
tools = wrapper.get_tools()         # OpenAI function-calling format
result = wrapper.run_tool("get_user_info", username="octocat")
```

---

### Does this work with FastAPI/Flask?

mcp_arena is not a FastAPI/Flask plugin, but you can run MCP servers alongside web frameworks:

**With FastAPI:**

```python
from fastapi import FastAPI
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.mcp.metrics import MetricsCollector

app = FastAPI()
server = GithubMCPServer(token="ghp_...", auto_register_tools=True)

@app.get("/metrics")
def get_metrics():
    return server.get_metrics()

@app.on_event("startup")
async def startup():
    # Run MCP server in background (SSE or streamable-http)
    import threading
    threading.Thread(target=server.run, kwargs={"transport": "sse"}, daemon=True).start()
```

For HTTP-based transports (`sse`, `streamable-http`), the MCP server exposes its own HTTP endpoints that can coexist with your web application on a different port.

---

### Can I use async operations?

Yes. Use `AsyncMCPLangChainIntegration` for async workflows:

```python
from mcp_arena.wrapper.langchain_integration import AsyncMCPLangChainIntegration

async with AsyncMCPLangChainIntegration(llm=llm) as integration:
    integration.add_github_server(token="ghp_...")
    await integration.initialize()
    result = await integration.invoke("List my repos")
```

---

### How do I orchestrate multiple agents?

Use the `MultiAgentOrchestrator`:

```python
from mcp_arena.agent.router import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()
orchestrator.register_agent("researcher", research_agent)
orchestrator.register_agent("writer", writer_agent)

# Define a sequential workflow
orchestrator.define_workflow("report", ["researcher", "writer"])
result = orchestrator.execute_workflow("report", "Analyze Q4 sales data")

# Or run agents in parallel
results = orchestrator.parallel_execute(
    ["researcher", "writer"],
    "Analyze Q4 sales data"
)
```

---

## Troubleshooting

### Server won't start — what should I check?

1. **Missing credentials.** Most presets require an API token or connection string. Check the error message — it usually tells you exactly what's missing:
   ```
   ValueError: GitHub token is required. Provide it as argument or set GITHUB_TOKEN environment variable.
   ```

2. **Port already in use.** If using SSE or streamable-http transport:
   ```bash
   # Find the process using the port
   # Linux/macOS
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```
   Change the port: `server = GithubMCPServer(token="...", port=8001)`

3. **Wrong transport.** The default transport is `stdio`. If you need HTTP access, set `transport="sse"` or `transport="streamable-http"`.

4. **Dependencies missing.** Install the preset-specific extras: `pip install mcp-arena[github]`.

---

### Authentication failing — common mistakes

| Mistake | Fix |
|---|---|
| Using a password instead of an API token | Jira, Confluence, Bitbucket Cloud all require **API tokens** or **app passwords**, not account passwords |
| Token has wrong scopes | GitHub needs at least `repo`, `read:org`, `read:user`; Slack needs `channels:read`, `chat:write` |
| Token expired or revoked | Regenerate from the provider's settings page |
| Wrong env var name | Double-check the exact name (e.g., `GITHUB_TOKEN` not `GH_TOKEN`) |
| `.env` file not loading | Ensure it's in the project root and `python-dotenv` is installed |
| Self-hosted URL not set | GitLab/Jira/Confluence self-hosted require a `url` parameter |

See [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for the complete env var reference.

---

### Port already in use — how to fix?

Option 1 — **Use a different port:**

```python
server = GithubMCPServer(token="...", port=8001)
```

Option 2 — **Kill the process using the port:**

```bash
# Linux/macOS
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Option 3 — **Use stdio transport** (no port needed):

```python
server.run(transport="stdio")  # default, no port binding
```

---

### `ModuleNotFoundError` when importing a preset

```
ModuleNotFoundError: No module named 'github'
```

Install the optional dependency group for that preset:

```bash
pip install mcp-arena[github]    # for GithubMCPServer
pip install mcp-arena[slack]     # for SlackMCPServer
pip install mcp-arena[postgres]  # for PostgresMCPServer
```

Or install everything: `pip install mcp-arena[all]`

---

### How do I enable debug mode?

Pass `debug=True` when creating a server:

```python
server = GithubMCPServer(token="...", debug=True)
```

Or set the log level for more detail:

```python
server = GithubMCPServer(token="...", log_level="DEBUG")
```

---

### Where can I get more help?

- **Documentation:** [https://mcparena.vercel.app/docs](https://mcparena.vercel.app/docs)
- **Troubleshooting guide:** [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Environment variables:** [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
- **GitHub Issues:** [https://github.com/SatyamSingh8306/mcp_arena/issues](https://github.com/SatyamSingh8306/mcp_arena/issues)
- **Discussions:** [https://github.com/SatyamSingh8306/mcp_arena/discussions](https://github.com/SatyamSingh8306/mcp_arena/discussions)
- **PyPI:** [https://pypi.org/project/mcp-arena/](https://pypi.org/project/mcp-arena/)
