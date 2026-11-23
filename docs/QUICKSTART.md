# Quick Start

## 1. Install

```bash
pip install mcp-arena
pip install "mcp-arena[github]"
pip install "mcp-arena[agents]" langchain-openai
pip install "mcp-arena[all]"
```

The core package includes `LocalOperationsMCPServer`, `GenericAPIMCPServer`, and `SMTPServer`. See [Installation](INSTALLATION.md) for the full extras list.

## 2. Run a preset server

```python
import os

from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"])
server.run()
```

Any MCP client can now connect to the process.

## 3. Choose a transport

```python
server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"])
server.run()

server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"], transport="sse", port=9001)
server.run()

server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"], transport="streamable-http", port=9001)
server.run()
```

`stdio` is the default and runs in-process. `sse` serves `http://<host>:<port>/sse`, and `streamable-http` serves `http://<host>:<port>/mcp`.

## 4. Hand a server to a LangChain agent

Install the `agents` extra and an LLM provider first.

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

## 5. Use multiple servers

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
from mcp_arena.agent import ToolRegistry

registry = ToolRegistry().register_server(slack_server)
registry.keep("chat_postMessage", "list_channels")

agent = await make_mcp_agent(llm, [slack_server], names=registry.names())
```

## 7. Add a non-MCP tool

```python
from mcp_arena.agent import BaseTool

class ShoutTool(BaseTool):
    def __init__(self):
        super().__init__(name="shout", description="Uppercase a string")

    def execute(self, text: str) -> str:
        return text.upper()

agent = await make_mcp_agent(llm, [github_server], extra_tools=[ShoutTool()])
```

## 8. Configure credentials

Most presets read credentials from environment variables. Importing `mcp_arena` loads a project-root `.env` file.

```text
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
NOTION_API_KEY=secret_xxxxxxxxxxxx
```

## 9. Use the CLI

```bash
mcp-arena list
mcp-arena info github
mcp-arena run --mcp-server github --token "$GITHUB_TOKEN"
```

## 10. Write a preset

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

Save the file as `mcp_arena/presents/hello.py`. The lazy loader discovers it automatically, so `from mcp_arena.presents import HelloServer` works.

## Next steps

- [Agent Guide](AGENT_GUIDE.md) — `make_mcp_agent`, `ToolRegistry`, forwarded `create_agent` parameters
- [LangChain Integration](LANGCHAIN_INTEGRATION.md) — multi-server agents, transports, sync wrapper
- [MCP Servers Guide](MCP_SERVERS_GUIDE.md) — every preset in one place
