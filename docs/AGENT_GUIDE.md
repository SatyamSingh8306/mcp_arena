# Agent Guide

> **Status:** the legacy `ReflectionAgent` / `ReactAgent` / `PlanningAgent` / `MultiAgentOrchestrator` / policies / memory systems are gone (see `CHANGELOG.md`, 0.4.0). `mcp_arena` now ships one thin function, `make_mcp_agent(llm, servers, ...)`, plus a tool registry for inspecting and filtering what those servers expose. The agent itself is whatever `langchain.agents.create_agent` returns — a compiled LangGraph.

---

## Table of contents
1. [TL;DR — `make_mcp_agent`](#tldr)
2. [How `make_mcp_agent` works](#how-it-works)
3. [Forwarded `create_agent` parameters](#forwarded-params)
4. [`ToolRegistry` — discover, filter, format](#tool-registry)
5. [Custom non-MCP tools](#custom-tools)
6. [Multi-server agents](#multi-server)
7. [Returning the agent — sync vs async](#sync-vs-async)
8. [Transport handling per server](#transport)
9. [Troubleshooting](#troubleshooting)

---

<a id="tldr"></a>
## 1. TL;DR — `make_mcp_agent`

```python
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.audio import AudioMCPServer
from mcp_arena.presents.image import ImageMCPServer

llm = ChatOpenAI(model="gpt-4o")

async def main():
    agent = await make_mcp_agent(
        llm,
        [AudioMCPServer(), ImageMCPServer()],
        system_prompt="You can edit audio and images.",
        name="media_agent",
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "trim the clip to 30s"}]}
    )
    print(result["messages"][-1].content)

asyncio.run(main())
```

That's it — one function, one await, one invocation. The agent picks the right tool on its own.

---

<a id="how-it-works"></a>
## 2. How `make_mcp_agent` works

```
make_mcp_agent(llm, servers, ...)
    │
    ├── For each BaseMCPServer instance, build a connection entry:
    │       stdio   →  {"transport": "stdio", "command": sys.executable,
    │       │             "args": ["-m", "mcp_arena.presents.<module>"]}
    │       sse     →  {"transport": "sse", "url": f"http://{host}:{port}/sse"}
    │       http    →  {"transport": "streamable_http",
    │                      "url": f"http://{host}:{port}/mcp"}
    │
    ├── MultiServerMCPClient(connections).get_tools()  ← one MCP round-trip
    │
    ├── Optional filters:
    │       names=[...]            keep only these tool names
    │       from_source("srv")     keep only one server's tools
    │       keep(...)/drop(...)    registry-driven
    │       extra_tools=[...]      append non-MCP tools
    │
    └── langchain.agents.create_agent(llm, tools, system_prompt=..., **kwargs)
            │
            └── returns a compiled LangGraph runnable
```

You get back the same shape `create_agent` returns. Call it with `.invoke(...)` (sync) or `.ainvoke(...)` (async). Inspect with `.get_graph().draw_mermaid()`.

---

<a id="forwarded-params"></a>
## 3. Forwarded `create_agent` parameters

Anything `create_agent` accepts is forwarded unchanged via `**create_agent_kwargs`. Reference: [`create_agent` (langchain v1)](https://reference.langchain.com/python/langchain/agents/factory/create_agent).

```python
agent = await make_mcp_agent(
    llm,
    servers,
    system_prompt="Confirm before editing.",

    # structural:
    middleware=[my_middleware],
    response_format=MyTypedDict,        # structured output
    state_schema=CustomAgentState,
    context_schema=MyContext,

    # persistence:
    checkpointer=InMemorySaver(),
    store=my_base_store,

    # human-in-the-loop:
    interrupt_before=["tools"],
    interrupt_after=["model"],

    # housekeeping:
    debug=True,
    name="my_agent",
    cache=my_cache,
    transformers=[...],
)
```

### Forwarded kwargs — verified by `tests/test_make_mcp_agent.py`

```python
async def test_forwards_arbitrary_kwargs_to_create_agent(...):
    ...
    await make_mcp_agent(
        llm, [server],
        checkpointer=checkpoint,
        store=store,
        middleware=middleware,
        state_schema=MyState,
        context_schema=MyContext,
        response_format=MyResponseFormat,
        debug=True,
        name="test_agent",
        interrupt_before=["tools"],
        interrupt_after=["model"],
    )
    # all 10 kwargs land on create_agent unchanged.
```

---

<a id="tool-registry"></a>
## 4. `ToolRegistry` — discover, filter, format

`make_mcp_agent` builds the agent's tool list from whatever the MCP servers expose. If you want to inspect, drop, rename, or only-forward the tools (for safety or to fit the model's context), use `ToolRegistry`:

```python
from mcp_arena.agent import ToolRegistry

reg = ToolRegistry()

# Pull every tool off one or more servers:
reg.register_server(audio_server)
reg.register_server(image_server)

# Inspect:
print(reg.names())          # ['convert_audio', 'detect_beats', 'analyze_audio', ...]
for spec in reg.list():
    print(spec.source, spec.name, "→", spec.description)

# Filter:
reg.keep("convert_audio", "detect_beats")         # drop everything else
# or:
reg.drop("delete_everything")                    # surgical removal
# or:
reg.from_source("AudioServer")                   # tools from one server only

# Rename (handy when two servers expose a tool with the same name):
reg.rename("convert_audio", "audio_convert")

# Hand the curated subset to the agent:
agent = await make_mcp_agent(
    llm,
    [audio_server, image_server],
    system_prompt="Audio tools only.",
    names=reg.names(),
)
```

### Output formats

```python
# OpenAI function-calling schema (for any OpenAI-style agent):
schemas = reg.to_openai()

# Plain `{name: callable}` for handing to LangChain / your own agent:
tools = reg.get_callables()
```

### `ToolSpec`

Each tool the registry knows about is a `ToolSpec`:

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    source: str                  # MCP server name, or "custom"
    function: Callable[..., Any]
    parameters: Dict[str, Any]
```

Use `spec.to_openai()` if you want OpenAI-format output for one tool.

---

<a id="custom-tools"></a>
## 5. Custom non-MCP tools

`BaseTool` is kept only as the subclass base for user-defined tools:

```python
from mcp_arena.agent import BaseTool

class ShoutTool(BaseTool):
    def __init__(self):
        super().__init__(name="shout", description="Uppercase a string")
    def execute(self, text: str) -> str:
        return text.upper()

agent = await make_mcp_agent(
    llm,
    [audio_server],
    extra_tools=[ShoutTool()],
)
```

`ToolRegistry.register(tool)` does the same thing and adds the tool to the inspection pool.

---

<a id="multi-server"></a>
## 6. Multi-server agents

Just pass a list — each server becomes its own connection in the underlying `MultiServerMCPClient`:

```python
from mcp_arena.presents.audio import AudioMCPServer
from mcp_arena.presents.browser import BrowserMCPServer
from mcp_arena.presents.image import ImageMCPServer

agent = await make_mcp_agent(
    llm,
    [AudioMCPServer(), BrowserMCPServer(), ImageMCPServer()],
    system_prompt="You can search, browse, and edit media.",
)

# `tools_name_prefix=True` is supported inside the underlying MCP client if you
# want names like "audio_convert_audio" instead of bare "convert_audio".
# To enable it, set `server_names` so the connection key is meaningful:
```

If your two servers expose tools with identical names, set `server_names={id(server): "alias"}` to disambiguate them, or use `ToolRegistry.rename(...)` after discovery.

---

<a id="sync-vs-async"></a>
## 7. Sync vs async

`make_mcp_agent` is async because that's the only API `MultiServerMCPClient.get_tools()` offers. If you can't `await`, use:

```python
from mcp_arena.agent import make_mcp_agent_sync

agent = make_mcp_agent_sync(
    llm,
    [audio_server],
    system_prompt="...",
)
```

It uses `asyncio.run()` internally — so don't call it from inside a running event loop.

---

<a id="transport"></a>
## 8. Transport handling per server

Each `BaseMCPServer` carries its own `transport` setting; `make_mcp_agent` chooses the right MCP-adapter connection entry based on it:

| `server.transport`    | MCP-adapter connection                                              |
| --------------------- | ------------------------------------------------------------------- |
| `"stdio"` (default)   | `{"transport": "stdio", "command": sys.executable, "args": ["-m", "mcp_arena.presents.<module>"]}` |
| `"sse"`               | `{"transport": "sse", "url": f"http://{host}:{port}/sse"}`           |
| `"http"` / `"streamable-http"` | `{"transport": "streamable_http", "url": f"http://{host}:{port}/mcp"}` |

For stdio servers, the builder spawns the MCP server as a subprocess via `python -m mcp_arena.presents.<module>`, where `<module>` is the file the server class lives in (e.g. `audio.py` for `AudioMCPServer`). This works because every preset in `mcp_arena.presents` is a self-contained Python module whose class has a no-arg-friendly signature (it pulls credentials from `os.getenv` or accepts them via constructor kwargs).

If you've subclassed `BaseMCPServer` outside `mcp_arena.presents`, the stdio auto-spawn won't find your module — start the server yourself and pass it over HTTP/SSE:

```python
server = MyCustomMCPServer()  # you manage lifecycle yourself
server.run(transport="streamable-http", port=9001, in_background=True)
agent = await make_mcp_agent(llm, [server], ...)
```

---

<a id="troubleshooting"></a>
## 9. Troubleshooting

**`ImportError: langchain_mcp_adapters not available`**
Install the `agents` extra: `pip install "mcp-arena[agents]"`.

**Server fails to launch in stdio mode**
Each preset expects either credentials in env vars (e.g. `SLACK_BOT_TOKEN`, `TWILIO_AUTH_TOKEN`, `GITHUB_TOKEN`) or `**kwargs` you passed to its constructor. Make sure these are set before the subprocess starts.

**Async / event-loop conflict**
If you're inside an async function, `await make_mcp_agent(...)` directly. If you're in synchronous code, use `make_mcp_agent_sync(...)`. Don't mix.

**What happened to `ReflectionAgent`?**
Gone. If you want self-reflection, do it client-side after the agent finishes: `await agent.ainvoke(prompt_for_v1)` → `await agent.ainvoke("Now critique the previous answer and improve it.")`.

**What happened to policies, memory, plans?**
Gone. `langgraph.checkpoint.memory.InMemorySaver()` (or any LangGraph `BaseStore` / `BaseCheckpoint`) covers persistence; structured prompts and reasoning live in `system_prompt` and `middleware`. The agent subsystem stays one function.
