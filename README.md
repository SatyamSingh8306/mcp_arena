# mcp_arena

[![PyPI version](https://badge.fury.io/py/mcp-arena.svg)](https://badge.fury.io/py/mcp-arena)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`mcp_arena`** is an opinionated Python library for building **MCP (Model Context Protocol) servers**: 30+ ready-to-use presets plus a one-line bridge into a LangChain agent.

```python
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer

async def main():
    agent = await make_mcp_agent(
        ChatOpenAI(model="gpt-4o"),
        [GithubMCPServer(token="ghp_…")],
        system_prompt="You can search GitHub.",
    )

asyncio.run(main())
```

> **0.4.0 release:** the old `ReflectionAgent` / `ReactAgent` / `PlanningAgent` / policies / memory / router stack is gone. The agent subsystem is now one function: `make_mcp_agent`. Migration guide in [`CHANGELOG.md`](CHANGELOG.md).

## Why mcp_arena?

- **30+ presets** covering Slack, GitHub, Notion, Gmail, PostgreSQL, Mongo, Redis, S3, browsers, video, audio, PDFs, QR codes, webscraping, and more — drop the file you need, install the matching extra, go.
- **One function to an agent.** Pass any combination of `BaseMCPServer` instances to `make_mcp_agent(llm, servers, ...)` and you get the exact same shape `langchain.agents.create_agent` returns — a compiled LangGraph. Forward any `create_agent` kwarg through `**kwargs`.
- **Optional tool filtering.** Don't overload the model with 40 tools — `ToolRegistry.register_server(s).keep("a", "b")` then pass `names=reg.names()`.
- **Lazy-loaded presets.** `mcp_arena.presents.__init__` AST-scans the directory; importing one preset doesn't pull in unrelated deps.
- **Drop-in extension.** New MCP server? Write a `*Server` subclass in `mcp_arena/presents/<name>.py`; it's auto-discovered.

## Install

```bash
pip install mcp-arena                       # core
pip install "mcp-arena[github,slack]"       # specific presets
pip install "mcp-arena[all]"                # all presets
pip install "mcp-arena[agents]"             # + langchain + MCP adapter
```

Python 3.12+. See [INSTALLATION.md](docs/INSTALLATION.md) for the full extras table.

## Use a preset

```python
from mcp_arena.presents.audio import AudioMCPServer

server = AudioMCPServer()              # reads credentials from env if needed
server.run()                           # stdio by default
```

Switch transports:

```python
server = AudioMCPServer(transport="sse", host="0.0.0.0", port=8001)
server.run()
```

## Build an agent from your servers

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

## Filter tools before they reach the model

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

## Add a custom (non-MCP) tool

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

## Available presets

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

The lazy loader in `mcp_arena.presents` AST-discovers every `*Server` class in the directory.

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

## Documents

- [**AGENT_GUIDE.md**](docs/AGENT_GUIDE.md) — `make_mcp_agent` reference, forwarded `create_agent` params, `ToolRegistry`
- [**LANGCHAIN_INTEGRATION.md**](docs/LANGCHAIN_INTEGRATION.md) — multi-server, transport choices, sync wrapper
- [**MCP_SERVERS_GUIDE.md**](docs/MCP_SERVERS_GUIDE.md) — every preset + custom-server instructions
- [**QUICKSTART.md**](docs/QUICKSTART.md) — 10-step walkthrough
- [**INSTALLATION.md**](docs/INSTALLATION.md) — extras reference
- [**TOOLS_GUIDE.md**](docs/TOOLS_GUIDE.md) — `ToolRegistry` / `BaseTool` / custom presets
- [**tutorial.md**](docs/tutorial.md) — end-to-end "Jarvis" build
- [**CHANGELOG.md**](CHANGELOG.md) — version history & migration guide

## CLI

```bash
mcp-arena list                 # every preset
mcp-arena run github --help    # preset-specific options
mcp-arena run github --token "$GITHUB_TOKEN"
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
