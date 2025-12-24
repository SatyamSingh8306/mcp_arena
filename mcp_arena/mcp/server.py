from abc import ABC, abstractmethod
from typing import Literal, Annotated, Optional, Collection, List, Callable, Any
from mcp.server.fastmcp import FastMCP
import functools

class BaseMCPServer(ABC):
    def __init__(
        self,
        name: str,
        description: str,
        host: Annotated[str, "Host on which MCP server runs"] = "127.0.0.1",
        port: Annotated[int, "Port on which MCP server runs"] = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
        mount_path: str = "/",
        sse_path: str = "/sse",
        message_path: str = "/messages/",
        streamable_http_path: str = "/mcp",
        json_response: bool = False,
        stateless_http: bool = False,
        dependencies: Collection[str] = (),
        auto_register_tools: bool = True
    ):
        """Initialize the base MCP server.
        
        Args:
            name: Server name
            description: Server description/instructions
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            log_level: Logging level
            mount_path: Mount path for HTTP server
            sse_path: SSE endpoint path
            message_path: Message endpoint path
            streamable_http_path: Streamable HTTP endpoint path
            json_response: Enable JSON response mode
            stateless_http: Enable stateless HTTP mode
            dependencies: Additional dependencies
            auto_register_tools: Automatically register tools on initialization
        """
        self.name = name
        self.description = description
        self.host = host
        self.port = port
        self.transport = transport
        self.debug = debug
        self.log_level = log_level
        
        self.mcp_server = FastMCP(
            name=name,
            instructions=description,
            host=host,
            port=port,
            debug=debug,
            log_level=log_level,
            mount_path=mount_path,
            sse_path=sse_path,
            message_path=message_path,
            streamable_http_path=streamable_http_path,
            json_response=json_response,
            stateless_http=stateless_http,
            dependencies=dependencies
        )
        
        # Store registered tools for reference
        self._registered_tools: List[str] = []

        if auto_register_tools:
            self._register_tools()

    @abstractmethod
    def _register_tools(self) -> None:
        """Register all tools with the MCP server."""
        pass

    def add_tool(self, tool: Annotated[Callable, "Tool function to add"], 
                 name: Optional[str] = None) -> Callable:
        """Register a tool with the MCP server.
        
        Args:
            tool: Tool function to add
            name: Optional custom name for the tool (defaults to function name)
            
        Returns:
            The decorated tool function
        """
        tool_name = name or tool.__name__
        description = tool.__doc__ or f"{tool_name} tool"
        
        # Register the tool
        decorated_tool = self.mcp_server.tool(
            name=tool_name,
            description=description
        )(tool)
        
        # Track registered tools
        self._registered_tools.append(tool_name)
        
        return decorated_tool
    
    def add_tools(self, tools: Annotated[List[Callable], "List of tools to add"]):
        """Register multiple tools at once.
        
        Args:
            tools: List of tool functions to add
        """
        for tool in tools:
            self.add_tool(tool)
    
    def add_tool_decorator(self, name: Optional[str] = None):
        """Create a decorator to add tools.
        
        Usage:
            @server.add_tool_decorator()
            def my_tool(): ...
            
            @server.add_tool_decorator(name="custom_name")
            def another_tool(): ...
        """
        def decorator(func: Callable) -> Callable:
            return self.add_tool(func, name=name)
        return decorator
    
    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names.
        
        Returns:
            List of registered tool names
        """
        return self._registered_tools.copy()

    def run(self, transport: Optional[Literal['stdio', 'sse', 'streamable-http']] = None) -> None:
        """Run the MCP server.
        
        Args:
            transport: Transport type (uses instance default if not specified)
        """
        transport_to_use = transport or self.transport
        self.mcp_server.run(transport=transport_to_use)
    
    def invoke(self, transport: Optional[Literal['stdio', 'sse', 'streamable-http']] = None) -> None:
        """Run the MCP server (alias for run)."""
        transport_to_use = transport or self.transport
        self.run(transport=transport_to_use)
    
    def __str__(self):
        return f"{self.name} \n {self.description}"

    def __repr__(self):
        return f"MCPServer(name='{self.name}', host='{self.host}', port={self.port})"