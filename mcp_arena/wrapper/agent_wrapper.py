"""Wrap an MCP server's registered tools for use by an agent."""
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass
class AgentTool:
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable


class MCPAgentWrapper:
    """Wrap an MCP server's tools into agent-callable functions."""

    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
        self.tools: List[AgentTool] = self._wrap_tools()
        self.tool_map: Dict[str, AgentTool] = {t.name: t for t in self.tools}

    def _wrap_tools(self) -> List[AgentTool]:
        """Read `_registered_tools` populated by `BaseMCPServer._sync_registered_tools`."""
        agent_tools = []
        for tool_name, tool_func in getattr(self.mcp_server, "_registered_tools", {}).items():
            agent_tools.append(AgentTool(
                name=tool_name,
                description=getattr(tool_func, "__doc__", "").strip().split("\n")[0] if getattr(tool_func, "__doc__", None) else f"Tool: {tool_name}",
                parameters={"type": "object", "properties": {}},
                function=self._make_wrapper(tool_func),
            ))
        return agent_tools

    def _make_wrapper(self, tool_func: Callable) -> Callable:
        def wrapper(**kwargs):
            try:
                return self._format_result(tool_func(**kwargs))
            except Exception as exc:
                return json.dumps({"error": str(exc), "success": False})
        wrapper.__name__ = getattr(tool_func, "__name__", "wrapped_tool")
        wrapper.__doc__ = getattr(tool_func, "__doc__", None)
        return wrapper

    def _format_result(self, result: Any) -> str:
        if isinstance(result, (dict, list)):
            return json.dumps(result, indent=2, default=str)
        return str(result)

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self.tools
        ]