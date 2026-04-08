from abc import ABC, abstractmethod
from typing import Literal, Annotated, Optional, Collection, List, Dict, Any
from mcp.server.fastmcp import FastMCP

from mcp_arena.mcp.metrics import MetricsCollector
from mcp_arena.mcp.dashboard import DashboardServer


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
        auto_register_tools: bool = True,
        enable_dashboard: bool = False,
        dashboard_port: int = 9090,
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
            enable_dashboard: Start a visual metrics dashboard on a separate port
            dashboard_port: Port for the metrics dashboard (default 9090)
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

        # Metrics & dashboard
        self.metrics = MetricsCollector(server_name=name)
        self._enable_dashboard = enable_dashboard
        self._dashboard_port = dashboard_port
        self._dashboard: Optional[DashboardServer] = None

        if auto_register_tools:
            self._register_tools()

    @abstractmethod
    def _register_tools(self) -> None:
        """Register all tools with the MCP server."""
        pass
    
    def __getattr__(self, name):
        return getattr(self.mcp_server, name)

    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names.
        
        Returns:
            List of registered tool names
        """
        return self._registered_tools.copy()

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def get_metrics(self) -> Dict[str, Any]:
        """Return current server metrics as a dictionary.
        
        Returns:
            Dictionary containing uptime, request counts, tool usage, etc.
        """
        return self.metrics.get_metrics()

    def start_dashboard(self, port: Optional[int] = None) -> str:
        """Start the metrics dashboard on a background thread.
        
        Args:
            port: Override the dashboard port (uses dashboard_port from init if not given).
        
        Returns:
            The dashboard URL.
        """
        dash_port = port or self._dashboard_port
        if self._dashboard is not None and self._dashboard.is_running:
            return self._dashboard.url
        self._dashboard = DashboardServer(
            metrics_collector=self.metrics,
            host="127.0.0.1",
            port=dash_port,
            server_name=self.name,
        )
        self._dashboard.start()
        return self._dashboard.url

    def stop_dashboard(self) -> None:
        """Stop the metrics dashboard if running."""
        if self._dashboard is not None:
            self._dashboard.stop()
            self._dashboard = None

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def run(self, transport: Optional[Literal['stdio', 'sse', 'streamable-http']] = None) -> None:
        """Run the MCP server.
        
        Args:
            transport: Transport type (uses instance default if not specified)
        """
        # Auto-start dashboard if enabled
        if self._enable_dashboard:
            self.start_dashboard()

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