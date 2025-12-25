from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
import json

@dataclass
class AgentTool:
    """Represents a tool that can be used by an AI agent."""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable

class MCPAgentWrapper:
    """Wraps MCP server tools into agent-compatible tools."""
    
    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
        self.tools = self._wrap_tools()
    
    def _wrap_tools(self) -> List[AgentTool]:
        """Wrap all registered MCP tools into agent tools."""
        agent_tools = []
        
        # For each tool in the MCP server, create an agent tool
        # This assumes your MCP server has a way to access its registered tools
        for tool_name, tool_func in self._get_mcp_tools():
            # Extract description and parameters from tool metadata
            description = self._extract_description(tool_func)
            parameters = self._extract_parameters(tool_func)
            
            # Create the agent tool
            agent_tool = AgentTool(
                name=tool_name,
                description=description,
                parameters=parameters,
                function=self._create_wrapper(tool_func)
            )
            agent_tools.append(agent_tool)
        
        return agent_tools
    
    def _get_mcp_tools(self) -> List[tuple]:
        """Get all tools from the MCP server.
        This needs to be implemented based on your MCP server structure.
        """
        tools = []
        
        # Example for Redis MCP Server
        if hasattr(self.mcp_server, '_registered_tools'):
            # If your MCP server stores tools in a registry
            for tool_name, tool_info in self.mcp_server._registered_tools.items():
                tools.append((tool_name, tool_info['function']))
        
        # Alternative: If using mcp_arena's decorator pattern
        elif hasattr(self.mcp_server.mcp_server, '_tools'):
            for tool_name, tool_func in self.mcp_server.mcp_server._tools.items():
                tools.append((tool_name, tool_func))
        
        return tools
    
    def _extract_description(self, tool_func: Callable) -> str:
        """Extract description from tool function."""
        if hasattr(tool_func, '__doc__') and tool_func.__doc__:
            return tool_func.__doc__.strip().split('\n')[0]
        return f"Tool: {tool_func.__name__}"
    
    def _extract_parameters(self, tool_func: Callable) -> Dict[str, Any]:
        """Extract parameter schema from tool function.
        This uses type hints to generate a JSON Schema.
        """
        import inspect
        from typing import get_type_hints
        
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Get function signature
        sig = inspect.signature(tool_func)
        type_hints = get_type_hints(tool_func)
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            param_type = type_hints.get(param_name, str)
            param_info = {
                "type": self._python_type_to_json_type(param_type),
                "description": f"Parameter: {param_name}"
            }
            
            # Add default value if exists
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            else:
                schema["required"].append(param_name)
            
            schema["properties"][param_name] = param_info
        
        return schema
    
    def _python_type_to_json_type(self, python_type):
        """Convert Python type to JSON Schema type."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null"
        }
        
        # Handle typing module types
        if hasattr(python_type, '__origin__'):
            if python_type.__origin__ is List:
                return "array"
            elif python_type.__origin__ is Dict:
                return "object"
            elif python_type.__origin__ is Optional:
                # Get the actual type inside Optional
                actual_type = python_type.__args__[0]
                return self._python_type_to_json_type(actual_type)
        
        # Handle Union types
        if hasattr(python_type, '__args__'):
            return [self._python_type_to_json_type(t) for t in python_type.__args__]
        
        # Return mapped type or default to string
        return type_map.get(python_type, "string")
    
    def _create_wrapper(self, tool_func: Callable) -> Callable:
        """Create a wrapper function that formats output for agents."""
        def wrapper(**kwargs):
            try:
                # Call the original MCP tool
                result = tool_func(**kwargs)
                
                # Format the result for agent consumption
                return self._format_result(result)
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False
                }
        
        # Preserve the original function name and docstring
        wrapper.__name__ = tool_func.__name__
        wrapper.__doc__ = tool_func.__doc__
        
        return wrapper
    
    def _format_result(self, result: Any) -> str:
        """Format tool result for agent consumption."""
        if isinstance(result, dict):
            # Check if it's an error
            if "error" in result:
                return f"Error: {result['error']}"
            
            # Pretty print dictionaries
            return json.dumps(result, indent=2)
        elif isinstance(result, list):
            return json.dumps(result, indent=2)
        elif isinstance(result, str):
            return result
        else:
            return str(result)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools in OpenAI-compatible format."""
        openai_tools = []
        
        for tool in self.tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        
        return openai_tools
    
    def run_tool(self, tool_name: str, **kwargs) -> str:
        """Run a specific tool by name."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.function(**kwargs)
        return f"Error: Tool '{tool_name}' not found"