# Tools Guide

`mcp_arena` only ships one tool concept: **MCP-server tools**. The agent pulls them off a `BaseMCPServer` instance and either passes them straight to a LangChain agent via `make_mcp_agent`, or routes them through `ToolRegistry` for inspection/filtering first.

If you want a tool that isn't an MCP server, subclass `BaseTool` (kept only for that purpose).

## Table of contents
1. [How tools reach an agent](#path)
2. [`ToolRegistry` — discover & filter](#registry)
3. [`BaseTool` — your own non-MCP tool](#base)
4. [Custom MCP presets](#custom-preset)
5. [Best practices](#best-practices)

---

<a id="path"></a>
## 1. How tools reach an agent

```
BaseMCPServer instance
    │  (registers tools via self.mcp_server.tool() inside _register_tools)
    │
    │  make_mcp_agent(llm, [server], ...)
    │     │
    │     ├── MultiServerMCPClient({server.name: connection}).get_tools()
    │     ├── (optional) ToolRegistry filter by name / source / rename
    │     ├── (optional) extra_tools=[BaseTool subclass]
    │     └── langchain.agents.create_agent(llm, tools, ...)
    │
    ▼
Compiled LangGraph runnable
```

A `BaseMCPServer` populates `self._registered_tools` (the dict of `{tool_name: function}`) at `_register_tools` time. Both the `MCPAgentWrapper` (for users not on LangChain) and `make_mcp_agent` read it.

---

<a id="registry"></a>
## 2. `ToolRegistry` — discover & filter

```python
from mcp_arena.agent import ToolRegistry, make_mcp_agent

reg = ToolRegistry()
reg.register_server(server_a)
reg.register_server(server_b)
reg.register(my_custom_tool)             # extra BaseTool

# Inspect:
print(reg.names())
for spec in reg.list():
    print(spec.source, spec.name, "→", spec.description)

# Mutate (all methods return self — chainable):
reg.keep("a", "b", "c")
reg.drop("debug_only")
reg.rename("a", "alpha")
reg.from_source("AudioServer")
```

### Output formats

```python
# Use with LangChain / OpenAI-style agents:
schemas = reg.to_openai()
# -> [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}, ...]

# Use with `make_mcp_agent`:
agent = await make_mcp_agent(llm, [server], names=reg.names())

# Get plain callables for your own agent:
tools = reg.get_callables()  # {'name': callable}
```

### `ToolSpec`

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    source: str                 # the server name, or "custom"
    function: Callable[..., Any]
    parameters: Dict[str, Any]
```

---

<a id="base"></a>
## 3. `BaseTool` — your own non-MCP tool

```python
from mcp_arena.agent import BaseTool, make_mcp_agent

class UpperTool(BaseTool):
    def __init__(self):
        super().__init__(name="uppercase", description="Capitalise a string")
    def execute(self, s: str) -> str:
        return s.upper()

# Inline:
agent = await make_mcp_agent(
    llm, [server], extra_tools=[UpperTool()],
)

# Or via the registry:
reg = ToolRegistry()
reg.register_server(server)
reg.register(UpperTool(), name="upper")     # override name
agent = await make_mcp_agent(llm, [server], names=reg.names())
```

> **Removed in 0.4.0:** `CalculatorTool`, `FileSystemTool`, `WebTool`, `DataAnalysisTool`, `TimeTool`, `SearchTool` — use MCP-server tools or subclass `BaseTool`.

---

<a id="custom-preset"></a>
## 4. Custom MCP presets

If your tool needs subprocess isolation, custom transports, or to expose many tools, write an MCP preset:

```python
# mcp_arena/presents/hello.py
from mcp_arena.mcp.server import BaseMCPServer

class HelloMCPServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp_server.tool()
        def greet(name: str) -> str:
            """Say hello to someone."""
            return f"Hello, {name}!"
```

Drop the file in `mcp_arena/presents/` and it'll be auto-discovered:

```python
from mcp_arena.presents import HelloMCPServer

server = HelloMCPServer(name="hello", description="Greeter")
```

See [`MCP_SERVERS_GUIDE.md`](MCP_SERVERS_GUIDE.md) § "Custom MCP Servers" for the full base-class spec.

---

<a id="best-practices"></a>
## 5. Best practices

**Don't overload the model.** A 30-tool agent is a 30-tool agent — drop the irrelevant ones before invoking:

```python
reg = ToolRegistry().register_server(server)
reg.drop("internal_admin", "test_endpoint")
agent = await make_mcp_agent(llm, [server], names=reg.names())
```

**Use `BaseTool` for trivial helpers.** If your "tool" is just `str.upper()`, don't spin up a whole MCP server — subclass `BaseTool` and pass via `extra_tools`.

**One preset, one transport.** Don't mix `stdio` and `http` on the same server. Each `BaseMCPServer` exposes a single `transport`; multi-transport setups mean multiple server instances.

**Pre-compute `parameters` schemas.** `BaseMCPServer` runs `self.mcp_server.tool()` on each tool, and FastMCP infers the JSON schema from your function signature. So write real type hints:

```python
def search(query: str, limit: int = 10) -> list[dict]:
    """Search docs."""
    ...
```
