# Agent Guide

`mcp_arena` exposes one agent function, `make_mcp_agent(llm, servers, ...)`, plus `ToolRegistry` for inspecting and filtering the tools those servers expose. The agent itself is whatever `langchain.agents.create_agent` returns: a compiled LangGraph runnable. The legacy `ReflectionAgent`, `ReactAgent`, `PlanningAgent`, policies, and memory subsystems were removed in 0.4.0; see [Changelog](../CHANGELOG.md).

## Contents

- [1. make_mcp_agent](#1-make_mcp_agent)
- [2. How it works](#2-how-it-works)
- [3. Forwarded create_agent parameters](#3-forwarded-create_agent-parameters)
- [4. ToolRegistry](#4-toolregistry)
- [5. Custom non-MCP tools](#5-custom-non-mcp-tools)
- [6. Multi-server agents](#6-multi-server-agents)
- [7. Sync vs async](#7-sync-vs-async)
- [8. Transport handling](#8-transport-handling)
- [9. Troubleshooting](#9-troubleshooting)

## 1. make_mcp_agent

```python
import asyncio

from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.audio import AudioMCPServer
from mcp_arena.presents.image import ImageMCPServer

async def main():
    agent = await make_mcp_agent(
        ChatOpenAI(model="gpt-4o"),
        [AudioMCPServer(), ImageMCPServer()],
        system_prompt="You can edit audio and images.",
        name="media_agent",
    )
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": "trim the clip to 30s"}]
    })
    print(result["messages"][-1].content)

asyncio.run(main())
```

## 2. How it works

```text
make_mcp_agent(llm, servers, ...)
    |
    +-- Build one connection entry per BaseMCPServer:
    |       stdio            -> python -m mcp_arena.presents.<module>
    |       sse              -> http://<host>:<port>/sse
    |       streamable-http  -> http://<host>:<port>/mcp
    |
    +-- MultiServerMCPClient(connections).get_tools()
    +-- Apply optional filters: names, from_source, keep/drop, extra_tools
    +-- langchain.agents.create_agent(llm, tools, system_prompt=..., **kwargs)
            |
            +-- compiled LangGraph runnable
```

Call the result with `.invoke(...)` or `.ainvoke(...)`. Inspect the graph with `.get_graph().draw_mermaid()`.

## 3. Forwarded create_agent parameters

Anything `create_agent` accepts is forwarded unchanged through `**create_agent_kwargs`. See the [create_agent reference](https://reference.langchain.com/python/langchain/agents/factory/create_agent).

```python
agent = await make_mcp_agent(
    llm,
    servers,
    system_prompt="Confirm before editing.",
    middleware=[my_middleware],
    response_format=MyTypedDict,
    state_schema=CustomAgentState,
    context_schema=MyContext,
    checkpointer=InMemorySaver(),
    store=my_base_store,
    interrupt_before=["tools"],
    interrupt_after=["model"],
    debug=True,
    name="my_agent",
    cache=my_cache,
    transformers=[...],
)
```

The parameters above are covered by `tests/test_make_mcp_agent.py`.

## 4. ToolRegistry

`make_mcp_agent` builds its tool list from whatever the servers expose. Use `ToolRegistry` to inspect, drop, rename, or forward a subset.

```python
from mcp_arena.agent import ToolRegistry

registry = ToolRegistry()
registry.register_server(audio_server)
registry.register_server(image_server)

print(registry.names())
for spec in registry.list():
    print(spec.source, spec.name, "->", spec.description)

registry.keep("convert_audio", "detect_beats")
registry.drop("delete_everything")
registry.from_source("AudioServer")
registry.rename("convert_audio", "audio_convert")

agent = await make_mcp_agent(
    llm,
    [audio_server, image_server],
    system_prompt="Audio tools only.",
    names=registry.names(),
)
```

Output formats:

```python
schemas = registry.to_openai()
callables = registry.get_callables()
```

Each entry returned by `list()` is a `ToolSpec`:

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    source: str
    function: Callable[..., Any]
    parameters: Dict[str, Any]
```

A spec's `source` is the MCP server name or `"custom"`. Use `spec.to_openai()` for a single OpenAI-format schema.

## 5. Custom non-MCP tools

`BaseTool` is the base class for user-defined tools:

```python
from mcp_arena.agent import BaseTool

class ShoutTool(BaseTool):
    def __init__(self):
        super().__init__(name="shout", description="Uppercase a string")

    def execute(self, text: str) -> str:
        return text.upper()

agent = await make_mcp_agent(llm, [audio_server], extra_tools=[ShoutTool()])
```

`ToolRegistry.register(tool)` adds the same kind of tool to the inspection pool.

## 6. Multi-server agents

Pass a list; each server becomes its own connection in `MultiServerMCPClient`:

```python
from mcp_arena.presents.browser import BrowserMCPServer

agent = await make_mcp_agent(
    llm,
    [audio_server, BrowserMCPServer(), image_server],
    system_prompt="You can search, browse, and edit media.",
)
```

If two servers expose tools with the same name, use `server_names={id(server): "alias"}` to make connection keys unique, or rename tools with `ToolRegistry.rename(...)`.

## 7. Sync vs async

`make_mcp_agent` is async because `MultiServerMCPClient.get_tools()` only exposes an async API. From synchronous code, use the wrapper:

```python
from mcp_arena.agent import make_mcp_agent_sync

agent = make_mcp_agent_sync(llm, [audio_server], system_prompt="...")
```

It uses `asyncio.run()` internally, so do not call it from inside a running event loop.

## 8. Transport handling

Each server carries its own `transport` setting, which the builder maps to an MCP-adapter connection:

| `server.transport` | MCP-adapter connection |
| --- | --- |
| `stdio` | `{"transport": "stdio", "command": sys.executable, "args": ["-m", "mcp_arena.presents.<module>"]}` |
| `sse` | `{"transport": "sse", "url": "http://<host>:<port>/sse"}` |
| `streamable-http` | `{"transport": "streamable_http", "url": "http://<host>:<port>/mcp"}` |

For stdio, the builder runs the server module as a subprocess. This works for bundled presets because each module is self-contained and can be constructed from environment variables. For a server defined in your own code, start it yourself and connect over SSE or `streamable-http`:

```python
server = MyCustomMCPServer()
server.run(transport="streamable-http")
agent = await make_mcp_agent(llm, [server], system_prompt="...")
```

## 9. Troubleshooting

**`ImportError: langchain_mcp_adapters not available`**

Install the agents extra: `pip install "mcp-arena[agents]"`.

**Server fails to launch in stdio mode**

Check that the preset's credentials are available as environment variables (for example `GITHUB_TOKEN`, `SLACK_BOT_TOKEN`, `TWILIO_AUTH_TOKEN`) or passed as constructor arguments. The subprocess inherits the parent environment.

**Async / event-loop conflict**

Use `await make_mcp_agent(...)` inside async code and `make_mcp_agent_sync(...)` from synchronous code. Do not mix them.

**Legacy agent classes**

`ReflectionAgent`, `ReactAgent`, `PlanningAgent`, policies, and memory were removed in 0.4.0. Persistence is provided by LangGraph checkpointers such as `langgraph.checkpoint.memory.InMemorySaver()`, and custom reasoning lives in `system_prompt` and middleware.
