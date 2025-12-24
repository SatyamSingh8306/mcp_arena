"""
Base classes and decorators for creating MCP tools.
"""

from typing import Callable, Any, Optional, Dict, List
from functools import wraps
import inspect


class Tool:
    """Base class for MCP tools."""
    
    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize a tool.
        
        Args:
            func: The function to wrap
            name: Tool name (defaults to function name)
            description: Tool description (defaults to function docstring)
            parameters: Tool parameters schema
        """
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or f"{self.name} tool"
        self.parameters = parameters or self._infer_parameters()
    
    def _infer_parameters(self) -> Dict[str, Any]:
        """Infer parameter schema from function signature."""
        sig = inspect.signature(self.func)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            param_info = {
                "type": "string",  # Default to string
                "description": f"Parameter {param_name}"
            }
            
            # Handle type hints
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif hasattr(param.annotation, '__origin__'):
                    if param.annotation.__origin__ is list:
                        param_info["type"] = "array"
            
            # Handle default values
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            
            parameters[param_name] = param_info
        
        return {
            "type": "object",
            "properties": parameters,
            "required": [name for name, param in sig.parameters.items() 
                         if param.default == inspect.Parameter.empty]
        }
    
    def __call__(self, *args, **kwargs):
        """Call the underlying function."""
        return self.func(*args, **kwargs)


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> Callable:
    """Decorator to create a tool from a function.
    
    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        parameters: Tool parameters schema
        
    Returns:
        Decorated function as a Tool
        
    Example:
        @tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b
    """
    def decorator(func: Callable) -> Tool:
        return Tool(func, name=name, description=description, parameters=parameters)
    
    return decorator
