# mcp_arena

[![PyPI version](https://badge.fury.io/py/mcp-arena.svg)](https://badge.fury.io/py/mcp-arena)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`mcp_arena`** is an opinionated Python library for building **MCP (Model Context Protocol) servers**: 30+ ready-to-use presets you can stand up in one call, plus a thin bridge into a LangChain agent.

The headline feature is the **MCP server** — drop one in, run it, talk to it over stdio / SSE / HTTP:

```python
# server.py
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(
    token="ghp_…",                        # or pull from $GITHUB_TOKEN
    host="127.0.0.1",
    port=8000,
    transport="stdio",                     # stdio (default) | sse | http
    debug=False,
)

if __name__ == "__main__":
    server.run()
```

Any MCP client can now talk to it. The full preset list, constructor kwargs, and `BaseMCPServer` surface are in [`MCP_SERVERS_GUIDE.md`](docs/MCP_SERVERS_GUIDE.md). The LangChain-agent bridge is at the bottom of this README — read after you've understood the server side.

> **0.4.0 release:** the old `ReflectionAgent` / `ReactAgent` / `PlanningAgent` / policies / memory / router stack is gone. The agent subsystem is now one function: `make_mcp_agent`. Migration guide in [`CHANGELOG.md`](CHANGELOG.md).

## Why mcp_arena?

- **30+ ready-to-run MCP server presets.** Slack, GitHub, Notion, Gmail, PostgreSQL, Mongo, Redis, S3, browsers, video, audio, PDFs, QR codes, webscraping, and more — install one extra, import one class, call `server.run()`. Any MCP-compatible client can talk to it.
- **Each preset is a real `BaseMCPServer`.** Tools register at construction, are exposed on `_registered_tools` for inspection, and the server can be started over stdio / SSE / HTTP in one call.
- **Lazy-loaded presets.** `mcp_arena.presents.__init__` AST-scans the directory; importing one preset doesn't pull in unrelated deps.
- **Drop-in extension.** New MCP server? Write a `*Server` subclass in `mcp_arena/presents/<name>.py`; it's auto-discovered.
- **Optional LangChain bridge.** `make_mcp_agent(llm, servers, ...)` is the only function that wires the same server objects into a LangGraph agent. Forward any `create_agent` kwarg through `**kwargs`.

## Install

> ⚠️ **`pip install mcp-arena` ships three general-purpose presets in core** — `LocalOperationsMCPServer`, `GenericAPIMCPServer`, and `SMTPServer` — so you can run a real MCP server with zero extra setup. Every other preset is gated behind an extra so you only pay for the third-party packages you actually need.

```bash
pip install mcp-arena                       # 3 core presets work out of the box
pip install "mcp-arena[github]"             # + GitHub preset (PyGithub)
pip install "mcp-arena[github,slack]"       # + several presets
pip install "mcp-arena[all]"                # + every preset (~30 packages)
pip install "mcp-arena[agents]"             # + LangChain bridge (langchain + MCP adapter)
```

What `pip install mcp-arena` **does** give you out of the box:
- `mcp_arena.mcp.server.BaseMCPServer` — the base class
- `mcp_arena.presents` lazy loader — every preset class is importable
- **`LocalOperationsMCPServer`** — file / system / process tools (uses `psutil` + `pyautogui`)
- **`GenericAPIMCPServer`** — make any HTTP API call (uses `httpx`)
- **`SMTPServer`** — send email via any SMTP server (pure stdlib)
- `mcp_arena.agent.make_mcp_agent` / `ToolRegistry` / `BaseTool`
- `mcp-arena` CLI (`mcp-arena list`, `mcp-arena run <preset>`)

What it **does not** install: anything else. If you try to instantiate a preset whose required dep isn't installed, you get a clear `ImportError` pointing at the exact install command — for example:

```
PyPDF2, fitz, pdfplumber and reportlab are required for this MCP server but are not installed.
Install it with:    pip install "mcp-arena[pdf]"
```

Pick the right extra from [INSTALLATION.md](docs/INSTALLATION.md) or [MCP_SERVERS.md](docs/MCP_SERVERS.md).

Python 3.12+. See [INSTALLATION.md](docs/INSTALLATION.md) for the full extras table.

## Run an MCP server

Every preset is a `BaseMCPServer` subclass. After construction, call `server.run()` to start serving.

### Stdio (default — works with any local MCP client)

```python
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(token="ghp_…")
server.run()                                        # transport="stdio"
```

Now point any MCP-compatible client at the process (e.g. Claude Desktop, Cursor, the `mcp-arena` CLI).

### HTTP / SSE (for remote clients)

```python
server = GithubMCPServer(token="ghp_…", transport="sse", host="0.0.0.0", port=8001)
server.run()
# -> listening on http://0.0.0.0:8001/sse

# or streamable-http:
server = GithubMCPServer(token="ghp_…", transport="http", port=8001)
server.run()
# -> listening on http://0.0.0.0:8001/mcp
```

| Transport         | Endpoint                        | When to use                       |
| ----------------- | ------------------------------- | --------------------------------- |
| `stdio` (default) | in-process via stdin/stdout     | local clients, the `make_mcp_agent` flow |
| `sse`             | `http://<host>:<port>/sse`      | browser clients, streaming        |
| `http`            | `http://<host>:<port>/mcp`      | multi-process / networked setups   |
| `streamable-http` | alias for `http`                | —                                 |

### Credentials: pass them in or pull from `os.environ`

```python
# Inline:
server = GithubMCPServer(token="ghp_…")

# Env-var fallback (most presets read these for you):
#   GITHUB_TOKEN, SLACK_BOT_TOKEN, NOTION_API_KEY, TWILIO_* …
server = GithubMCPServer()                          # picks up GITHUB_TOKEN
```

`from mcp_arena import …` calls `python-dotenv.load_dotenv()` for you, so a project-root `.env` is read automatically.

### From the CLI

```bash
# List every preset mcp_arena knows about
mcp-arena list

# Show options for one preset
mcp-arena run github --help

# Start a server (stdio by default; pass --transport sse|http for network)
mcp-arena run github --token "$GITHUB_TOKEN"
mcp-arena run github --token "$GITHUB_TOKEN" --transport sse --host 0.0.0.0 --port 8001
```

### Use a preset programmatically without the MCP protocol

You don't have to speak MCP — `BaseMCPServer` exposes the registered tools directly:

```python
server = AudioMCPServer()
for tool_name in server.get_registered_tools():
    print(tool_name)

# Or wrap them as plain Python callables:
from mcp_arena.wrapper import MCPAgentWrapper
for tool in MCPAgentWrapper(server).get_tools():
    print(tool["function"]["name"])
```

See [`MCP_SERVERS_GUIDE.md`](docs/MCP_SERVERS_GUIDE.md) for the full preset list, the `BaseMCPServer` constructor surface, and how to write your own.

---

## Available presets

Every preset is one extra. Install what you need; nothing else gets pulled in.

### Communication
`slack`, `whatsapp`, `gmail`, `outlook`, `smtp`, `mail`, `notification`

### Dev platforms
`github`, `gitlab`, `bitbucket`

### Productivity
`notion`, `confluence`, `jira`

### Data & storage
`postgres`, `mongo`, `redis`, `vectordb`

### Cloud / OS
`aws` (S3), `cloudstorage`, `docker`, `local_operation`, `screencapture`

### Browser / web / media
`browser`, `webscraping`, `generic_api`, `image`, `video`, `audio`, `pdf`, `qrcode`, `spreadsheet`

See [`docs/MCP_SERVERS_GUIDE.md`](docs/MCP_SERVERS_GUIDE.md) for the full table, kwargs, and transport notes.

## Write your own preset

```python
# mcp_arena/presents/greeter.py
from mcp_arena.mcp.server import BaseMCPServer

class GreeterMCPServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp_server.tool()
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}!"

# Now importable:
from mcp_arena.presents import GreeterMCPServer
```

The lazy loader in `mcp_arena.presents` AST-discovers every `*Server` class in the directory. Drop the file, import the class — done.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 mcp_arena.presents                      │
│  ~30 *MCPServer subclasses (auto-discovered)           │
│  Browser · Slack · GH · Postgres · AWS · ...            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                BaseMCPServer.run()                      │
│  stdio / sse / http — talks to any MCP client           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (optional)
┌─────────────────────────────────────────────────────────┐
│                   mcp_arena.agent                        │
│  • make_mcp_agent(llm, servers, ...)  → LangGraph agent  │
│  • ToolRegistry (register / keep / drop / rename /      │
│    to_openai / get_callables)                           │
│  • BaseTool (subclass-this for non-MCP tools)           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│   langchain.agents.create_agent → langgraph runnable    │
│   (compiled via langchain-mcp-adapters.MultiServerMCP…) │
└─────────────────────────────────────────────────────────┘
```

The MCP-server layer is the product. The agent layer is a thin add-on that wraps the same server objects with a LangGraph.

## Documents

- [MCP Servers](docs/MCP_SERVERS.md) — quick reference: every preset, what extra to install, what env vars each reads, ready-to-copy install commands.
- [MCP Servers Guide](docs/MCP_SERVERS_GUIDE.md) — every preset in detail; `BaseMCPServer` constructor surface; how to write your own.
- [Quick Start](docs/QUICKSTART.md) — 10-step walkthrough.
- [Installation Guide](docs/INSTALLATION.md) — full extras table (one entry per preset / per group).
- [Tools Guide](docs/TOOLS_GUIDE.md) — `ToolRegistry`, `BaseTool`, custom MCP presets.

Agent & LangChain docs (read after the server-side docs above):

- [Agent Guide](docs/AGENT_GUIDE.md) — `make_mcp_agent` reference, forwarded `create_agent` params, troubleshooting.
- [**LANGCHAIN_INTEGRATION.md**](docs/LANGCHAIN_INTEGRATION.md) — multi-server, transport choices, sync wrapper, migration from 0.3.x.
- [**tutorial.md**](docs/tutorial.md) — end-to-end "Jarvis" build (local-fs + GitHub agent).
- [**CHANGELOG.md**](CHANGELOG.md) — version history & migration guide.

## Bonus: wire a server to a LangChain agent

If you already have a LangChain workflow and want to give it access to MCP tools, `make_mcp_agent` is the one-line bridge:

```python
import asyncio, os
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.presents.slack import SlackMCPServer

async def main():
    agent = await make_mcp_agent(
        ChatOpenAI(model="gpt-4o"),
        [
            GithubMCPServer(token=os.environ["GITHUB_TOKEN"]),
            SlackMCPServer(token=os.environ["SLACK_BOT_TOKEN"]),
        ],
        system_prompt="You can search GitHub and post to Slack.",
        name="devops_bot",
    )
    out = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Find the top-3 starred repos in my org and post links to #general.",
        }],
    })
    print(out["messages"][-1].content)

asyncio.run(main())
```

`make_mcp_agent` handles the connection between MCP-server transports and the LangChain `MultiServerMCPClient`, then forwards to `langchain.agents.create_agent`. See [`LANGCHAIN_INTEGRATION.md`](docs/LANGCHAIN_INTEGRATION.md).

### Filter tools before they reach the model

```python
from mcp_arena.agent import ToolRegistry, make_mcp_agent

reg = ToolRegistry().register_server(slack_server)
print("Available:", reg.names())         # ['chat_postMessage', 'list_channels', ...]
reg.keep("chat_postMessage", "list_channels")

agent = await make_mcp_agent(
    ChatOpenAI(model="gpt-4o"),
    [slack_server],
    names=reg.names(),                   # only these tools become agent tools
)
```

### Add a custom (non-MCP) tool

```python
from mcp_arena.agent import BaseTool, make_mcp_agent

class ShoutTool(BaseTool):
    def __init__(self):
        super().__init__(name="shout", description="Uppercase a string")
    def execute(self, s: str) -> str:
        return s.upper()

agent = await make_mcp_agent(
    ChatOpenAI(model="gpt-4o"),
    [slack_server],
    extra_tools=[ShoutTool()],
)
```

## Contributing

```bash
git clone https://github.com/SatyamSingh8306/mcp_arena
cd mcp_arena
pip install -e ".[complete]"
pytest
black .
ruff check .
mypy mcp_arena
```

Priority areas: new presets, bug fixes, doc accuracy.

## Requirements

- Python 3.12+
- An MCP-compatible client to actually consume the servers (or use `make_mcp_agent` to wire one into LangChain)
- Optional: your LLM provider's `langchain-*` adapter for the agent flow

## License

MIT — see [LICENSE](LICENSE).

## Links

- [GitHub repository](https://github.com/SatyamSingh8306/mcp_arena)
- [Issue tracker](https://github.com/SatyamSingh8306/mcp_arena/issues)
- [PyPI](https://pypi.org/project/mcp-arena/)
- [CHANGELOG](CHANGELOG.md)
