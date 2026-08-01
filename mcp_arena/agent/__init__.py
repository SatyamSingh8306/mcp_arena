"""Agent-side helpers for mcp_arena.

The public surface is small:

- `make_mcp_agent(llm, servers, ...)` — async, returns a compiled LangGraph
  whose tools come from the given `BaseMCPServer` instances.
- `make_mcp_agent_sync(...)` — sync wrapper for the same.
- `ToolRegistry` / `BaseTool` / `tool_registry` — discover, filter, and
  format MCP-server tools before passing them to an agent.
"""
from .builder import Agent, make_mcp_agent, make_mcp_agent_sync
from .tools import BaseTool, ToolRegistry, ToolSpec, tool_registry

__all__ = [
    "Agent",
    "BaseTool",
    "ToolRegistry",
    "ToolSpec",
    "make_mcp_agent",
    "make_mcp_agent_sync",
    "tool_registry",
]