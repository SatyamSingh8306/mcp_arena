"""Agent-side tool registry.

`ToolRegistry` discovers tools exposed by MCP servers (via
`BaseMCPServer._registered_tools`), lets the user inspect them, drop
or rename them, and hand a customized subset to an agent.

Ponytail: the only built-in tool class kept here is `BaseTool` — it
exists so users can subclass it when they want to add a non-MCP tool
to their agent. The legacy CalculatorTool/FilesystemTool/etc. presets
were removed; MCP servers cover those use cases.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSpec:
    """Inspectable description of one tool, with a callable to invoke it."""

    name: str
    description: str
    source: str  # MCP server name, or "custom" for user-defined tools
    function: Callable[..., Any]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_openai(self) -> Dict[str, Any]:
        """Format as an OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }


class BaseTool:
    """Base class for user-defined (non-MCP) tools.

    Subclass and implement `execute`. Register with `ToolRegistry.register`.
    """

    def __init__(self, name: str, description: str, parameters: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.parameters = parameters or {"type": "object", "properties": {}}

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError

    def to_spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            source="custom",
            function=self.execute,
            parameters=self.parameters,
        )


class ToolRegistry:
    """Discover, filter, and format tools before handing them to an agent."""

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    # -------- discovery --------
    def register_server(self, server) -> "ToolRegistry":
        """Pull every `_registered_tools` entry off a BaseMCPServer instance."""
        source = getattr(server, "name", server.__class__.__name__)
        for tool_name, tool_func in getattr(server, "_registered_tools", {}).items():
            self._tools[tool_name] = ToolSpec(
                name=tool_name,
                description=(getattr(tool_func, "__doc__", "") or "").strip().split("\n")[0]
                or f"Tool: {tool_name}",
                source=source,
                function=tool_func,
                parameters={"type": "object", "properties": {}},
            )
        return self

    def register(self, tool: BaseTool, name: Optional[str] = None) -> "ToolRegistry":
        """Add a user-defined tool (subclass of BaseTool)."""
        spec = tool.to_spec()
        if name:
            spec.name = name
        self._tools[spec.name] = spec
        return self

    # -------- filtering --------
    def keep(self, *names: str) -> "ToolRegistry":
        """Drop everything except the named tools. Returns self for chaining."""
        keep = set(names)
        self._tools = {n: t for n, t in self._tools.items() if n in keep}
        return self

    def drop(self, *names: str) -> "ToolRegistry":
        """Remove the named tools. Returns self for chaining."""
        for n in names:
            self._tools.pop(n, None)
        return self

    def rename(self, old: str, new: str) -> "ToolRegistry":
        """Rename a tool in-place. Returns self for chaining."""
        if old in self._tools:
            self._tools[new] = self._tools.pop(old)
            self._tools[new].name = new
        return self

    def from_source(self, source: str) -> "ToolRegistry":
        """Drop everything not from the given MCP server. Returns self."""
        self._tools = {n: t for n, t in self._tools.items() if t.source == source}
        return self

    # -------- output --------
    def names(self) -> List[str]:
        return sorted(self._tools)

    def list(self) -> List[ToolSpec]:
        return [self._tools[n] for n in self.names()]

    def to_openai(self) -> List[Dict[str, Any]]:
        """Format all current tools as OpenAI function-calling schemas."""
        return [t.to_openai() for t in self.list()]

    def get_callables(self) -> Dict[str, Callable[..., Any]]:
        """Return `{name: function}` for handing to a LangChain/etc. agent."""
        return {n: self._tools[n].function for n in self.names()}


# Singleton convenience: `from mcp_arena.agent.tools import tool_registry`
tool_registry = ToolRegistry()


__all__ = ["BaseTool", "ToolRegistry", "ToolSpec", "tool_registry"]