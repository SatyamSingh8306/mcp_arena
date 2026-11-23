# mcp_arena

[![PyPI](https://img.shields.io/pypi/v/mcp-arena.svg)](https://pypi.org/project/mcp-arena/)
[![Version](https://img.shields.io/badge/version-0.5.0-blue.svg)](CHANGELOG.md)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

`mcp_arena` is a Python library for building [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers. It ships 30+ ready-to-run presets and a small base class for writing your own. Servers speak standard MCP over stdio, SSE, or streamable HTTP, so any MCP-compatible client can connect to them.

## Features

- **30+ MCP server presets** — GitHub, Slack, Notion, PostgreSQL, MongoDB, Redis, S3, Context7, PDF, browser, and more.
- **One-call servers** — import a class, call `server.run()`, and serve over stdio, SSE, or streamable HTTP.
- **Small extension surface** — every preset is a `BaseMCPServer` subclass that registers its tools at construction.
- **Lazy loading** — presets are auto-discovered and import only their own dependencies.
- **Client-agnostic** — one server works with any MCP client; no agent framework is required.

## Installation

Requires Python 3.12 or newer.

```bash
pip install mcp-arena
```

The core install includes three presets that work immediately: `LocalOperationsMCPServer`, `GenericAPIMCPServer`, and `SMTPServer`. All other presets are optional extras:

```bash
pip install "mcp-arena[github]"
pip install "mcp-arena[github,slack,postgres]"
pip install "mcp-arena[all]"
pip install "mcp-arena[agents]" langchain-openai
```

Constructing a preset without its extra raises an `ImportError` containing the exact install command. See [Installation Guide](docs/INSTALLATION.md) for the full extras table.

## Quick start

Create a server:

```python
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(token="ghp_...")
server.run()
```

Any MCP client can now connect to it. The same thing from the CLI:

```bash
mcp-arena list
mcp-arena info github
mcp-arena run --mcp-server github --token "$GITHUB_TOKEN"
```

## Usage

### Transports

| Transport | Endpoint | Use case |
| --- | --- | --- |
| `stdio` (default) | stdin/stdout | Local MCP clients, `make_mcp_agent` |
| `sse` | `http://<host>:<port>/sse` | Browser and streaming clients |
| `streamable-http` | `http://<host>:<port>/mcp` | Networked or multi-process setups |

```python
server = GithubMCPServer(token="ghp_...", transport="sse", host="0.0.0.0", port=8001)
server.run()
```

### Credentials

Presets take credentials as constructor arguments or read them from the environment. Importing `mcp_arena` loads a project-root `.env` file.

```python
server = GithubMCPServer(token="ghp_...")
server = GithubMCPServer()  # reads GITHUB_TOKEN
```

### Inspect registered tools

Tools can be used without an MCP client:

```python
from mcp_arena.presents.audio import AudioMCPServer
from mcp_arena.wrapper import MCPAgentWrapper

server = AudioMCPServer()
print(server.get_registered_tools())

for tool in MCPAgentWrapper(server).get_tools():
    print(tool["function"]["name"])
```

### Write a preset

```python
from mcp_arena.mcp.server import BaseMCPServer

class GreeterMCPServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp_server.tool()
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}!"
```

Save it as `mcp_arena/presents/greeter.py`; the lazy loader makes it importable as `from mcp_arena.presents import GreeterMCPServer`.

### Optional: LangChain agent

This bridge is an optional extra; the servers above work with any MCP client on their own. To use it, install `mcp-arena[agents]` and an LLM provider. `make_mcp_agent` is the only function needed to turn servers into a LangGraph agent's tools.

```python
import asyncio
import os

from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer

async def main():
    agent = await make_mcp_agent(
        ChatOpenAI(model="gpt-4o"),
        [GithubMCPServer(token=os.environ["GITHUB_TOKEN"])],
        system_prompt="You can search GitHub.",
    )
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": "List my repos"}]
    })
    print(result["messages"][-1].content)

asyncio.run(main())
```

Use `ToolRegistry` to limit which tools reach the model:

```python
from mcp_arena.agent import ToolRegistry

registry = ToolRegistry().register_server(server)
registry.keep("search_repositories", "list_repositories")

agent = await make_mcp_agent(llm, [server], names=registry.names())
```

## Available presets

Each row lists the extra to install. Presets marked *core* ship with `pip install mcp-arena`.

### Communication

`slack`, `whatsapp`, `gmail`, `outlook`, `smtp`, `mail`, `notification`

### Dev platforms

`github`, `gitlab`, `bitbucket`

### Productivity

`notion`, `confluence`, `jira`

### Data and storage

`postgres`, `mongo`, `redis`, `vectordb`

### Monitoring and documentation

`sentry` (read-only error investigation), `context7` (current, version-specific library docs)

```python
from mcp_arena.presents.context7 import Context7MCPServer

server = Context7MCPServer()
server.run()
```

### Cloud and OS

`aws` (S3), `cloudstorage`, `docker`, `local_operation` (core), `screencapture`

### Browser, web, and media

`browser`, `webscraping`, `generic_api` (core), `image`, `video`, `audio`, `pdf`, `qrcode`, `spreadsheet`

See [MCP Servers](docs/MCP_SERVERS.md) for the full preset table, required extras, and environment variables, or [MCP Servers Guide](docs/MCP_SERVERS_GUIDE.md) for constructor options and custom presets.

## Documentation

- [Installation Guide](docs/INSTALLATION.md) — extras reference and verification steps
- [Quick Start](docs/QUICKSTART.md) — short walkthrough
- [MCP Servers](docs/MCP_SERVERS.md) — presets, extras, credentials, CLI
- [MCP Servers Guide](docs/MCP_SERVERS_GUIDE.md) — `BaseMCPServer` and custom presets
- [Tools Guide](docs/TOOLS_GUIDE.md) — `ToolRegistry` and `BaseTool`
- [Agent Guide](docs/AGENT_GUIDE.md) — `make_mcp_agent` reference
- [LangChain Integration](docs/LANGCHAIN_INTEGRATION.md) — multi-server agents and transports
- [Tutorial](docs/tutorial.md) — end-to-end local-filesystem + GitHub agent
- [Changelog](CHANGELOG.md) — version history and migration notes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
