from typing import Any, Dict, List, Optional, Callable
from .interfaces import IAgentTool


class BaseTool(IAgentTool):
    """Base implementation for agent tools"""
    
    def __init__(self, name: str, description: str, schema: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.schema = schema or {}
    
    def get_description(self) -> str:
        return f"{self.name}: {self.description}"
    
    def get_schema(self) -> Dict[str, Any]:
        return self.schema.copy()


class SearchTool(BaseTool):
    """Tool for performing searches"""
    
    def __init__(self, search_function: Callable[[str], List[str]]):
        super().__init__(
            name="search",
            description="Search for information using the provided query",
            schema={"query": "string", "type": "search query"}
        )
        self.search_function = search_function
    
    def execute(self, query: str, **kwargs) -> List[str]:
        """Execute search with the given query"""
        try:
            results = self.search_function(query)
            return results if isinstance(results, list) else [str(results)]
        except Exception as e:
            return [f"Search error: {str(e)}"]


class CalculatorTool(BaseTool):
    """Tool for performing calculations"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations",
            schema={"expression": "string", "type": "mathematical expression"}
        )
    
    def execute(self, expression: str, **kwargs) -> str:
        """Execute mathematical calculation"""
        try:
            # Safe evaluation of mathematical expressions
            import ast
            import operator
            
            # Define safe operators
            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.Mod: operator.mod,
                ast.USub: operator.neg,
            }
            
            def eval_node(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.Expression):
                    return eval_node(node.body)
                elif isinstance(node, ast.BinOp):
                    left = eval_node(node.left)
                    right = eval_node(node.right)
                    op_type = type(node.op)
                    if op_type in operators:
                        return operators[op_type](left, right)
                    else:
                        raise ValueError(f"Unsupported operator: {op_type}")
                elif isinstance(node, ast.UnaryOp):
                    operand = eval_node(node.operand)
                    op_type = type(node.op)
                    if op_type in operators:
                        return operators[op_type](operand)
                    else:
                        raise ValueError(f"Unsupported unary operator: {op_type}")
                else:
                    raise ValueError(f"Unsupported expression type: {type(node)}")
            
            # Parse and evaluate the expression
            tree = ast.parse(expression, mode='eval')
            result = eval_node(tree)
            
            return str(result)
        except Exception as e:
            return f"Calculation error: {str(e)}"


class FileSystemTool(BaseTool):
    """Tool for file system operations"""
    
    def __init__(self, base_path: str = "."):
        super().__init__(
            name="filesystem",
            description="Perform file system operations like read, write, list files",
            schema={
                "operation": "string",
                "path": "string",
                "content": "string (optional)"
            }
        )
        self.base_path = base_path
    
    def execute(self, operation: str, path: str, content: Optional[str] = None, **kwargs) -> str:
        """Execute file system operation"""
        import os
        
        try:
            full_path = os.path.join(self.base_path, path)
            
            if operation == "read":
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                else:
                    return f"File not found: {full_path}"
            
            elif operation == "write":
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content or "")
                return f"Successfully wrote to: {full_path}"
            
            elif operation == "list":
                if os.path.exists(full_path):
                    items = os.listdir(full_path)
                    return f"Contents of {full_path}:\n" + "\n".join(items)
                else:
                    return f"Directory not found: {full_path}"
            
            elif operation == "exists":
                return f"Path exists: {os.path.exists(full_path)}"
            
            else:
                return f"Unsupported operation: {operation}"
        
        except Exception as e:
            return f"File system error: {str(e)}"


class WebTool(BaseTool):
    """Tool for web operations"""
    
    def __init__(self):
        super().__init__(
            name="web",
            description="Perform web operations like fetch webpage content",
            schema={"url": "string", "operation": "string"}
        )
    
    def execute(self, operation: str, url: str, **kwargs) -> str:
        """Execute web operation"""
        try:
            if operation == "fetch":
                import requests
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.text[:2000]  # Limit to first 2000 characters
            
            elif operation == "headers":
                import requests
                response = requests.head(url, timeout=10)
                response.raise_for_status()
                return str(dict(response.headers))
            
            else:
                return f"Unsupported web operation: {operation}"
        
        except Exception as e:
            return f"Web operation error: {str(e)}"


class DataAnalysisTool(BaseTool):
    """Tool for data analysis operations"""
    
    def __init__(self):
        super().__init__(
            name="data_analysis",
            description="Perform basic data analysis on provided data",
            schema={"data": "string/list", "operation": "string"}
        )
    
    def execute(self, operation: str, data: Any, **kwargs) -> str:
        """Execute data analysis operation"""
        try:
            if operation == "summarize":
                if isinstance(data, str):
                    # Text summary
                    words = len(data.split())
                    chars = len(data)
                    lines = len(data.split('\n'))
                    return f"Text summary: {words} words, {chars} characters, {lines} lines"
                
                elif isinstance(data, list):
                    # List summary
                    return f"List summary: {len(data)} items"
                
                else:
                    return f"Data type: {type(data).__name__}"
            
            elif operation == "statistics":
                if isinstance(data, list) and all(isinstance(x, (int, float)) for x in data):
                    import statistics
                    return {
                        "count": len(data),
                        "mean": statistics.mean(data),
                        "median": statistics.median(data),
                        "min": min(data),
                        "max": max(data)
                    }
                else:
                    return "Statistics only available for numeric lists"
            
            else:
                return f"Unsupported data operation: {operation}"
        
        except Exception as e:
            return f"Data analysis error: {str(e)}"


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self._tools: Dict[str, type] = {}
        self._instances: Dict[str, IAgentTool] = {}
    
    def register_tool(self, name: str, tool_class: type) -> None:
        """Register a tool class"""
        self._tools[name] = tool_class
    
    def create_tool(self, name: str, **kwargs) -> IAgentTool:
        """Create an instance of a registered tool"""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not registered")
        
        tool_instance = self._tools[name](**kwargs)
        self._instances[name] = tool_instance
        return tool_instance
    
    def get_tool(self, name: str) -> Optional[IAgentTool]:
        """Get an existing tool instance"""
        return self._instances.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def create_default_tools(self) -> List[IAgentTool]:
        """Create a set of default tools"""
        tools = [
            CalculatorTool(),
            FileSystemTool(),
            WebTool(),
            DataAnalysisTool()
        ]
        
        # Store instances
        for tool in tools:
            self._instances[tool.name] = tool
        
        return tools


# Global tool registry instance
tool_registry = ToolRegistry()

# Register default tools
tool_registry.register_tool("calculator", CalculatorTool)
tool_registry.register_tool("filesystem", FileSystemTool)
tool_registry.register_tool("web", WebTool)
tool_registry.register_tool("data_analysis", DataAnalysisTool)
