# Quick Start

## 1. Install

```bash
pip install mcp-arena                      # core
pip install mcp-arena[github]              # + GitHub preset
pip install mcp-arena[agents]              # + LangChain agent helper
pip install mcp-arena[all]                 # every preset
```

## 2. Use a preset MCP server

```python
import os
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"])
server.run()
```

That's it. Any MCP client can now talk to it.

## 3. Use the preset over stdio (default) or HTTP

```python
# Stdio (default — runs in-process; good for local MCP clients)
server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"])
server.run()

# HTTP — exposed over the network
server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"], transport="http", port=9001)
server.run()

# SSE — server-sent events
server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"], transport="sse", port=9001)
server.run()
```

## 4. Hand a server to a LangChain agent

```python
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer

async def main():
    llm = ChatOpenAI(model="gpt-4o")
    agent = await make_mcp_agent(
        llm,
        [GithubMCPServer(token=os.environ["GITHUB_TOKEN"])],
        system_prompt="You can search GitHub.",
    )
    out = await agent.ainvoke({
        "messages": [{"role": "user", "content": "List my repos"}]
    })
    print(out["messages"][-1].content)

asyncio.run(main())
```

## 5. Multiple servers, one agent

```python
agent = await make_mcp_agent(
    llm,
    [
        GithubMCPServer(token=os.environ["GITHUB_TOKEN"]),
        SlackMCPServer(token=os.environ["SLACK_BOT_TOKEN"]),
    ],
    system_prompt="You can search GitHub and post to Slack.",
)
```

## 6. Filter tools before they reach the agent

```python
from mcp_arena.agent import make_mcp_agent, ToolRegistry

reg = ToolRegistry().register_server(slack_server)
reg.keep("chat_postMessage", "list_channels")  # only these tools reach the agent

agent = await make_mcp_agent(
    llm,
    [slack_server],
    names=reg.names(),
)
```

## 7. Add a non-MCP tool

```python
from mcp_arena.agent import BaseTool, make_mcp_agent

class ShoutTool(BaseTool):
    def __init__(self):
        super().__init__(name="shout", description="Uppercase a string")
    def execute(self, text: str) -> str:
        return text.upper()

agent = await make_mcp_agent(
    llm,
    [github_server],
    extra_tools=[ShoutTool()],
)
```

## 8. Environment variables

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
NOTION_API_KEY=secret_xxxxxxxxxxxx
```

`mcp_arena` calls `python-dotenv.load_dotenv()` at import time (`from mcp_arena import ...`), so a `.env` at the project root is picked up automatically.

## 9. Run from the CLI

```bash
# List available presets
mcp-arena list

# Show the help for one preset
mcp-arena run github --help

# Start a server
mcp-arena run github --token "$GITHUB_TOKEN"
```

## 10. Write your own preset

```python
from mcp_arena.mcp.server import BaseMCPServer

class HelloServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp_server.tool()
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}!"

HelloServer(name="hello", description="Greeter").run()
```

Save as `mcp_arena/presents/hello.py` and it'll be auto-discovered by the lazy `mcp_arena.presents` loader — `from mcp_arena.presents import HelloServer` will Just Work.

---

Next:
- **[AGENT_GUIDE.md](AGENT_GUIDE.md)** — `make_mcp_agent`, `ToolRegistry`, forwarded `create_agent` params
- **[LANGCHAIN_INTEGRATION.md](LANGCHAIN_INTEGRATION.md)** — multi-server, transport choices, sync wrapper
- **[MCP_SERVERS_GUIDE.md](MCP_SERVERS_GUIDE.md)** — every preset in one place
