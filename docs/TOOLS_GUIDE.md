# Tools Guide

`mcp_arena` has one primary tool concept: tools exposed by MCP servers. `make_mcp_agent` can pass them straight to a LangChain agent, or you can route them through `ToolRegistry` to inspect and filter them first. For non-MCP helpers, subclass `BaseTool`.

## Contents

- [1. How tools reach an agent](#1-how-tools-reach-an-agent)
- [2. ToolRegistry](#2-toolregistry)
- [3. BaseTool](#3-basetool)
- [4. Custom MCP presets](#4-custom-mcp-presets)
- [5. Best practices](#5-best-practices)

## 1. How tools reach an agent

```text
BaseMCPServer instance
    |
    |  registers tools with FastMCP inside _register_tools()
    |  make_mcp_agent(llm, [server], ...)
    |     |
    |     +-- MultiServerMCPClient(...).get_tools()
    |     +-- optional ToolRegistry filtering
    |     +-- optional extra_tools=[BaseTool subclass]
    |     +-- langchain.agents.create_agent(llm, tools, ...)
    v
Compiled LangGraph runnable
```

A `BaseMCPServer` populates `_registered_tools` (a `{name: function}` mapping) during construction. Both `MCPAgentWrapper` and `make_mcp_agent` read it.

## 2. ToolRegistry

```python
from mcp_arena.agent import ToolRegistry, make_mcp_agent

registry = ToolRegistry()
registry.register_server(server_a)
registry.register_server(server_b)
registry.register(my_custom_tool)

print(registry.names())
for spec in registry.list():
    print(spec.source, spec.name, "->", spec.description)

registry.keep("a", "b", "c")
registry.drop("debug_only")
registry.rename("a", "alpha")
registry.from_source("AudioServer")
```

All mutating methods return `self`, so calls can be chained.

Output formats:

```python
schemas = registry.to_openai()
callables = registry.get_callables()

agent = await make_mcp_agent(llm, [server], names=registry.names())
```

`to_openai()` returns OpenAI function-calling schemas; `get_callables()` returns a `{name: callable}` mapping.

Each item in `registry.list()` is a `ToolSpec`:

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    source: str
    function: Callable[..., Any]
    parameters: Dict[str, Any]
```

## 3. BaseTool

```python
from mcp_arena.agent import BaseTool, ToolRegistry, make_mcp_agent

class UpperTool(BaseTool):
    def __init__(self):
        super().__init__(name="uppercase", description="Capitalise a string")

    def execute(self, text: str) -> str:
        return text.upper()

agent = await make_mcp_agent(llm, [server], extra_tools=[UpperTool()])

registry = ToolRegistry()
registry.register_server(server)
registry.register(UpperTool(), name="upper")
agent = await make_mcp_agent(llm, [server], names=registry.names())
```

The canned tools (`CalculatorTool`, `FileSystemTool`, `WebTool`, `DataAnalysisTool`, `TimeTool`, `SearchTool`) were removed in 0.4.0. Use MCP-server tools or subclass `BaseTool`.

## 4. Custom MCP presets

For tools that need subprocess isolation, custom transports, or a group of related functions, write an MCP preset:

```python
from mcp_arena.mcp.server import BaseMCPServer

class HelloMCPServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp_server.tool()
        def greet(name: str) -> str:
            """Say hello to someone."""
            return f"Hello, {name}!"
```

Save it as `mcp_arena/presents/hello.py` and it is discovered automatically:

```python
from mcp_arena.presents import HelloMCPServer

server = HelloMCPServer(name="hello", description="Greeter")
```

See [MCP Servers Guide](MCP_SERVERS_GUIDE.md#4-custom-presets) for the full base-class specification.

## 5. Best practices

- **Limit the tool set.** Drop irrelevant tools before invoking the agent:

  ```python
  registry = ToolRegistry().register_server(server)
  registry.drop("internal_admin", "test_endpoint")
  agent = await make_mcp_agent(llm, [server], names=registry.names())
  ```

- **Use `BaseTool` for trivial helpers.** A one-line transformation does not need an MCP server; pass it through `extra_tools`.
- **Use one transport per server instance.** A `BaseMCPServer` exposes a single `transport`; use separate instances for multiple transports.
- **Write real type hints.** FastMCP infers the JSON schema of each tool from its signature:

  ```python
  def search(query: str, limit: int = 10) -> list[dict]:
      """Search docs."""
      ...
  ```
