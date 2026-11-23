# LangChain Integration

`mcp_arena` provides one bridge from MCP servers to a LangChain agent: `mcp_arena.agent.make_mcp_agent`. It builds a LangGraph runnable whose tools come from one or more `BaseMCPServer` instances. The older `MCPLangChainIntegration` and `MCPLangChainWrapper` classes were removed in 0.4.0; see [Changelog](../CHANGELOG.md).

## Install

```bash
pip install "mcp-arena[agents]"
pip install langchain-openai
```

The `agents` extra installs `langchain>=1.0,<2.0` and `langchain-mcp-adapters>=0.1,<1.0`. Install the LLM provider you use (`langchain-openai`, `langchain-anthropic`, `langchain-groq`, and so on) separately.

## Minimal example

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

Passing an empty `servers` list raises a `ValueError` with a clear message.

## What it does

```text
make_mcp_agent(llm, servers, ...)
    |
    +-- Derive one MCP-adapter connection per server:
    |       stdio            -> python -m mcp_arena.presents.<module>
    |       sse              -> http://<host>:<port>/sse
    |       streamable-http  -> http://<host>:<port>/mcp
    |
    +-- MultiServerMCPClient(connections).get_tools()
    +-- Apply optional filters and extra tools
    +-- langchain.agents.create_agent(llm, tools, system_prompt=..., **kwargs)
            |
            +-- compiled LangGraph runnable
```

You do not manage subprocesses, sessions, or cleanup; stdio servers stop when the client closes.

## Filter tools

```python
from mcp_arena.agent import ToolRegistry

registry = ToolRegistry().register_server(slack_server)
print(registry.names())
registry.keep("chat_postMessage", "list_channels")

agent = await make_mcp_agent(llm, [slack_server], names=registry.names())
```

See [Agent Guide](AGENT_GUIDE.md#4-toolregistry) for the full registry API.

## Mix MCP and non-MCP tools

```python
from mcp_arena.agent import BaseTool

class UpperTool(BaseTool):
    def __init__(self):
        super().__init__(name="uppercase", description="Capitalise a string")

    def execute(self, text: str) -> str:
        return text.upper()

agent = await make_mcp_agent(llm, [slack_server], extra_tools=[UpperTool()])
```

## Forwarded create_agent parameters

Everything `langchain.agents.create_agent` accepts is forwarded through `**create_agent_kwargs`.

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = await make_mcp_agent(
    llm,
    [github_server, slack_server],
    system_prompt="Always confirm before posting.",
    checkpointer=InMemorySaver(),
    interrupt_before=["tools"],
    name="devops_bot",
    debug=True,
)
```

See the [Agent Guide](AGENT_GUIDE.md#3-forwarded-create_agent-parameters) for the full list of forwarded arguments.

## Multiple servers

Pass a list. Tool names may collide, so disambiguate when needed:

```python
agent = await make_mcp_agent(
    llm,
    [server_a, server_b],
    server_names={id(server_a): "alpha", id(server_b): "beta"},
)
```

Use `ToolRegistry.rename(...)` if two servers expose the same tool name.

## Transports

| `server.transport` | Builder behavior |
| --- | --- |
| `stdio` | Spawns `python -m mcp_arena.presents.<module>` and talks over stdin/stdout |
| `sse` | Connects to `http://<host>:<port>/sse` |
| `streamable-http` | Connects to `http://<host>:<port>/mcp` using adapter transport `streamable_http` |

Set the transport on the server side:

```python
AudioMCPServer(transport="sse", host="0.0.0.0", port=8001)
```

## Sync wrapper

`make_mcp_agent` is async because the MCP adapter only exposes an async `get_tools()`. For synchronous code:

```python
from mcp_arena.agent import make_mcp_agent_sync

agent = make_mcp_agent_sync(llm, [server], system_prompt="...")
```

It calls `asyncio.run()` internally, so do not use it from inside a running event loop.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `ValueError: make_mcp_agent requires at least one MCP server` | The `servers` list is empty. |
| `ImportError: langchain_mcp_adapters` | Install `pip install "mcp-arena[agents]"`. |
| Server fails to start in stdio mode | Credentials are missing from the environment. |
| Subprocess keeps spawning but the agent times out | The server constructor needs credentials up front; pass them in. |
| `RuntimeError: asyncio.run() cannot be called...` | `make_mcp_agent_sync()` was called from inside an event loop. Use `await make_mcp_agent(...)`. |

## Migrating from 0.3.x

```python
from mcp_arena.agent import make_mcp_agent

agent = await make_mcp_agent(
    llm,
    [github_server],
    system_prompt="...",
)
result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "..."}]
})
```

The previous `MCPLangChainWrapper.connect()` / `create_agent()` / `invoke_agent()` flow is no longer needed; pass the server objects directly. See the [0.4.0 migration guide](../CHANGELOG.md#migration-guide-03x-to-040).
