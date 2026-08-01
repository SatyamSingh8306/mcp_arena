"""Wrappers around mcp_arena MCP servers.

- `MCPAgentWrapper(server)` — read an MCP server's registered tools and
  surface them as agent-callable Python functions (no langchain needed).
- `make_mcp_agent(llm, servers, ...)` lives in `mcp_arena.agent.builder`.
"""

from .agent_wrapper import AgentTool, MCPAgentWrapper

__all__ = ["AgentTool", "MCPAgentWrapper"]